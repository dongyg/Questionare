#coding:utf-8
__all__ = ['add_task','delete_task']

import heapq, thread, time, traceback
from datetime import datetime,timedelta

_tasks = [] # a heap
_task_count = 0 # 用来维护新任务的TASK_ID字段。2个task tuple在排序比较时，tuple的START_TIME字段加上这个字段总可以决定先后
_mutex = thread.allocate_lock() # for _tasks and _task_count

def _schedule_tasks():
    ''' 本模块内部用的任务调度线程函数 '''
    START_TIME, TASK_ID, NEXT_TIME, INTERVAL, FN, ARGS, KW = 0, 1, 2, 3, 4, 5, 6
    while True:
        _mutex.acquire()
        while _tasks:
            task = _tasks[0] # peek
            start_time = task[START_TIME]
            now = datetime.now()
            if start_time > now:
                break
            task = heapq.heappop(_tasks)
            try:
                thread.start_new_thread(task[FN], task[ARGS], task[KW])
            except Exception as e:
                traceback.print_exc()
            interval = task[INTERVAL]
            next_time = task[NEXT_TIME]
            if interval:
                heapq.heappush(_tasks, (now+interval,task[TASK_ID],[],interval,task[FN],task[ARGS],task[KW]))
            elif next_time:
                heapq.heappush(_tasks, (next_time[0],task[TASK_ID],next_time[1:],None,task[FN],task[ARGS],task[KW]))
        _mutex.release()
        time.sleep(0.075) # 75ms

thread.start_new_thread(_schedule_tasks,())

def add_task(fn,args=(),kw=None, start_time=(), seconds=0,minutes=0,hours=0,days=0,weeks=0):
    ''' 添加新任务：
            fn：任务函数
            args：任务函数的参数
            kw：任务函数的关键字参数
            start_time：任务的开始时间，为datetime.datetime或datetime tuple/list类型；
                不设置的话默认为当前时间；若有设置多个start_time，则认为是多时间点执行，会忽略掉下面的执行周期的设置
            seconds/minutes/hours/days/weeks：用于叠加设置任务的执行周期，若叠加得到的周期<=0秒，那么任务只执行一次
            返回任务id
    '''
    assert callable(fn) and isinstance(args,tuple) and (kw is None or isinstance(kw,dict)) and \
            (not start_time or isinstance(start_time,datetime) or isinstance(start_time,(list,tuple))
                and all((isinstance(x,datetime) for x in start_time)))
    if kw is None:
        kw = {}
    if not start_time:
        start_time = [datetime.now()]
    elif isinstance(start_time,datetime):
        start_time = [start_time]
    else:
        start_time = sorted(set(start_time))
    if len(start_time) > 1:
        interval = None
    else:
        interval = timedelta(seconds=seconds,minutes=minutes,hours=hours,days=days,weeks=weeks)
        if interval <= timedelta(0):
            interval = None

    _mutex.acquire()
    global _task_count
    _task_count += 1
    task_id = _task_count
    heapq.heappush(_tasks, (start_time[0],task_id,start_time[1:],interval,fn,args,kw))
    _mutex.release()
    return task_id

def delete_task(task_id):
    ''' 删除任务 '''
    _mutex.acquire()
    if 1<= task_id <= _task_count:
        for i, task in enumerate(_tasks):
            if task[1] == task_id:
                del _tasks[i]
                heapq.heapify(_tasks) #
                break
    _mutex.release()

def _test_task(*args, **kw):
    now = datetime.now()
    f = open('_test_task.txt', 'a')
    print str(now)
    print >>f, str(now)
    print '   ',
    print >>f, '   ',
    for arg in args:
        print repr(arg),
        print >>f, repr(arg),
    print
    print >>f
    for k,v in kw.items():
        print '    ' + k + ': ' + repr(v)
        print >>f, '    ' + k + ': ' + repr(v)
    f.close()

def foo(a, b, c):
    print datetime.now()
    print a, b, c

if __name__=='__main__':
    delta = timedelta(seconds=5)
    now = datetime.now()
    task1_id = None
    try:
        task1_id = add_task(_test_task, (1,'abc',[1,2]), {'a':11,'b':22}, start_time=(now+delta*3,now+delta*2,now+delta,now), seconds=2)
    except:
        traceback.print_exc()
    task2_id = None
    try:
        task2_id = add_task(foo, (1, 2), {'c':3}, seconds=3)
        # add_task(foo, (1, 2, 3), seconds=3)
    except:
        traceback.print_exc()
    while True: # 作为主线程
        delete_task(6)
        # delete_task(task1_id)
        delete_task(task2_id)
        time.sleep(1)