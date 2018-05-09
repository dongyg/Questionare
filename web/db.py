#coding:utf-8
"""
Database API
(part of web.py)
"""

__all__ = [
  "UnknownParamstyle", "UnknownDB", "TransactionError",
  "sqllist", "sqlors", "reparam", "sqlquote",
  "SQLQuery", "SQLParam", "sqlparam",
  "SQLLiteral", "sqlliteral",
  "database", 'DB',
]

import time
try:
    import datetime
except ImportError:
    datetime = None

try: set
except NameError:
    from sets import Set as set

from utils import threadeddict, storage, iters, iterbetter, safestr, safeunicode

try:
    # db module can work independent of web.py
    from webapi import debug, config
except:
    import sys
    debug = sys.stderr
    config = storage()

def callShell(cmd):
    """执行shell命令，返回命令执行的返回内容"""
    import subprocess,traceback,platform
    try:
        p = subprocess.Popen(args=cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (stdoutput,erroutput) = p.communicate()
        retval = stdoutput
    except Exception, e:
        traceback.print_exc()
        retval = e
    if platform.system()=='Windows':
        retval = unicode(retval, 'gbk')
    return retval.strip()

class UnknownDB(Exception):
    """raised for unsupported dbms"""
    pass

class _ItplError(ValueError):
    def __init__(self, text, pos):
        ValueError.__init__(self)
        self.text = text
        self.pos = pos
    def __str__(self):
        return "unfinished expression in %s at char %d" % (
            repr(self.text), self.pos)

class TransactionError(Exception): pass

class UnknownParamstyle(Exception):
    """
    raised for unsupported db paramstyles

    (currently supported: qmark, numeric, format, pyformat)
    """
    pass

class SQLParam(object):
    """
    Parameter in SQLQuery.

        >>> q = SQLQuery(["SELECT * FROM test WHERE name=", SQLParam("joe")])
        >>> q
        <sql: "SELECT * FROM test WHERE name='joe'">
        >>> q.query()
        'SELECT * FROM test WHERE name=%s'
        >>> q.values()
        ['joe']
    """
    __slots__ = ["value"]

    def __init__(self, value):
        self.value = value

    def get_marker(self, paramstyle='pyformat'):
        if paramstyle == 'qmark':
            return '?'
        elif paramstyle == 'numeric':
            return ':1'
        elif paramstyle is None or paramstyle in ['format', 'pyformat']:
            return '%s'
        raise UnknownParamstyle, paramstyle

    def sqlquery(self):
        return SQLQuery([self])

    def __add__(self, other):
        return self.sqlquery() + other

    def __radd__(self, other):
        return other + self.sqlquery()

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return '<param: %s>' % repr(self.value)

sqlparam =  SQLParam

class SQLQuery(object):
    """
    You can pass this sort of thing as a clause in any db function.
    Otherwise, you can pass a dictionary to the keyword argument `vars`
    and the function will call reparam for you.

    Internally, consists of `items`, which is a list of strings and
    SQLParams, which get concatenated to produce the actual query.
    """
    __slots__ = ["items"]

    # tested in sqlquote's docstring
    def __init__(self, items=None):
        r"""Creates a new SQLQuery.

            >>> SQLQuery("x")
            <sql: 'x'>
            >>> q = SQLQuery(['SELECT * FROM ', 'test', ' WHERE x=', SQLParam(1)])
            >>> q
            <sql: 'SELECT * FROM test WHERE x=1'>
            >>> q.query(), q.values()
            ('SELECT * FROM test WHERE x=%s', [1])
            >>> SQLQuery(SQLParam(1))
            <sql: '1'>
        """
        if items is None:
            self.items = []
        elif isinstance(items, list):
            self.items = items
        elif isinstance(items, SQLParam):
            self.items = [items]
        elif isinstance(items, SQLQuery):
            self.items = list(items.items)
        else:
            self.items = [items]

        # Take care of SQLLiterals
        from decimal import Decimal
        for i, item in enumerate(self.items):
            if isinstance(item, SQLParam) and isinstance(item.value, SQLLiteral):
                if isinstance(item, SQLParam) and isinstance(item.value,Decimal):
                    self.items[i] = str(item)
                else:
                    self.items[i] = item.value.v

    def append(self, value):
        self.items.append(value)

    def __add__(self, other):
        if isinstance(other, basestring):
            items = [other]
        elif isinstance(other, SQLQuery):
            items = other.items
        else:
            return NotImplemented
        return SQLQuery(self.items + items)

    def __radd__(self, other):
        if isinstance(other, basestring):
            items = [other]
        else:
            return NotImplemented

        return SQLQuery(items + self.items)

    def __iadd__(self, other):
        if isinstance(other, (basestring, SQLParam)):
            self.items.append(other)
        elif isinstance(other, SQLQuery):
            self.items.extend(other.items)
        else:
            return NotImplemented
        return self

    def __len__(self):
        return len(self.query())

    def query(self, paramstyle=None):
        """
        Returns the query part of the sql query.
            >>> q = SQLQuery(["SELECT * FROM test WHERE name=", SQLParam('joe')])
            >>> q.query()
            'SELECT * FROM test WHERE name=%s'
            >>> q.query(paramstyle='qmark')
            'SELECT * FROM test WHERE name=?'
        """
        s = []
        for x in self.items:
            if isinstance(x, SQLParam):
                x = x.get_marker(paramstyle)
                s.append(safestr(x))
            else:
                x = safestr(x)
                # automatically escape % characters in the query
                # For backward compatability, ignore escaping when the query looks already escaped
                if paramstyle in ('format', 'pyformat'):
                    if '%' in x and '%%' not in x:
                        x = x.replace('%', '%%')
                s.append(x)
        return "".join(s)

    def values(self):
        """
        Returns the values of the parameters used in the sql query.
            >>> q = SQLQuery(["SELECT * FROM test WHERE name=", SQLParam('joe')])
            >>> q.values()
            ['joe']
        """
        return [i.value for i in self.items if isinstance(i, SQLParam)]

    def join(items, sep=' ', prefix=None, suffix=None, target=None):
        """
        Joins multiple queries.

        >>> SQLQuery.join(['a', 'b'], ', ')
        <sql: 'a, b'>

        Optinally, prefix and suffix arguments can be provided.

        >>> SQLQuery.join(['a', 'b'], ', ', prefix='(', suffix=')')
        <sql: '(a, b)'>

        If target argument is provided, the items are appended to target instead of creating a new SQLQuery.
        """
        if target is None:
            target = SQLQuery()

        target_items = target.items

        if prefix:
            target_items.append(prefix)

        from decimal import Decimal
        for i, item in enumerate(items):
            if i != 0:
                target_items.append(sep)
            if isinstance(item, SQLQuery):
                target_items.extend(item.items)
            elif isinstance(item, SQLParam) and isinstance(item.value,Decimal):
                # 20160720 dongyg: Decimal会以 Decimal('1.1000') 形式插入的问题
                target_items.append(str(item))
            else:
                target_items.append(item)

        if suffix:
            target_items.append(suffix)
        return target

    join = staticmethod(join)

    def _str(self):
        try:
            return self.query() % tuple([sqlify(x) for x in self.values()])
        except (ValueError, TypeError):
            return self.query()

    def __str__(self):
        return safestr(self._str())

    def __unicode__(self):
        return safeunicode(self._str())

    def __repr__(self):
        return '<sql: %s>' % repr(str(self))

class SQLLiteral:
    """
    Protects a string from `sqlquote`.

        >>> sqlquote('NOW()')
        <sql: "'NOW()'">
        >>> sqlquote(SQLLiteral('NOW()'))
        <sql: 'NOW()'>
    """
    def __init__(self, v):
        self.v = v

    def __repr__(self):
        return self.v

sqlliteral = SQLLiteral

def _sqllist(values):
    """
        >>> _sqllist([1, 2, 3])
        <sql: '(1, 2, 3)'>
    """
    items = []
    items.append('(')
    for i, v in enumerate(values):
        if i != 0:
            items.append(', ')
        items.append(sqlparam(v))
    items.append(')')
    return SQLQuery(items)

def reparam(string_, dictionary):
    """
    Takes a string and a dictionary and interpolates the string
    using values from the dictionary. Returns an `SQLQuery` for the result.

        >>> reparam("s = $s", dict(s=True))
        <sql: "s = 't'">
        >>> reparam("s IN $s", dict(s=[1, 2]))
        <sql: 's IN (1, 2)'>
    """
    dictionary = dictionary.copy() # eval mucks with it
    vals = []
    result = []
    for live, chunk in _interpolate(string_):
        if live:
            v = eval(chunk, dictionary)
            result.append(sqlquote(v))
        else:
            result.append(chunk)
    return SQLQuery.join(result, '')

def sqlify(obj):
    """
    converts `obj` to its proper SQL version

        >>> sqlify(None)
        'NULL'
        >>> sqlify(True)
        "'t'"
        >>> sqlify(3)
        '3'
    """
    # because `1 == True and hash(1) == hash(True)`
    # we have to do this the hard way...

    if obj is None:
        return 'NULL'
    elif obj is True:
        return "'t'"
    elif obj is False:
        return "'f'"
    elif datetime and isinstance(obj, datetime.datetime):
        return repr(obj.isoformat())
    else:
        if isinstance(obj, unicode): obj = obj.encode('utf8')
        return repr(obj)

def sqllist(lst):
    """
    Converts the arguments for use in something like a WHERE clause.

        >>> sqllist(['a', 'b'])
        'a, b'
        >>> sqllist('a')
        'a'
        >>> sqllist(u'abc')
        u'abc'
    """
    if isinstance(lst, basestring):
        return lst
    else:
        return ', '.join(lst)

def sqlors(left, lst):
    """
    `left is a SQL clause like `tablename.arg = `
    and `lst` is a list of values. Returns a reparam-style
    pair featuring the SQL that ORs together the clause
    for each item in the lst.

        >>> sqlors('foo = ', [])
        <sql: '1=2'>
        >>> sqlors('foo = ', [1])
        <sql: 'foo = 1'>
        >>> sqlors('foo = ', 1)
        <sql: 'foo = 1'>
        >>> sqlors('foo = ', [1,2,3])
        <sql: '(foo = 1 OR foo = 2 OR foo = 3 OR 1=2)'>
    """
    if isinstance(lst, iters):
        lst = list(lst)
        ln = len(lst)
        if ln == 0:
            return SQLQuery("1=2")
        if ln == 1:
            lst = lst[0]

    if isinstance(lst, iters):
        return SQLQuery(['('] +
          sum([[left, sqlparam(x), ' OR '] for x in lst], []) +
          ['1=2)']
        )
    else:
        return left + sqlparam(lst)

def sqlwhere(dictionary, grouping=' AND '):
    """
    Converts a `dictionary` to an SQL WHERE clause `SQLQuery`.

        >>> sqlwhere({'cust_id': 2, 'order_id':3})
        <sql: 'order_id = 3 AND cust_id = 2'>
        >>> sqlwhere({'cust_id': 2, 'order_id':3}, grouping=', ')
        <sql: 'order_id = 3, cust_id = 2'>
        >>> sqlwhere({'a': 'a', 'b': 'b'}).query()
        'a = %s AND b = %s'
    """
    return SQLQuery.join([k + ' = ' + sqlparam(v) for k, v in dictionary.items()], grouping)

def sqlquote(a):
    """
    Ensures `a` is quoted properly for use in a SQL query.

        >>> 'WHERE x = ' + sqlquote(True) + ' AND y = ' + sqlquote(3)
        <sql: "WHERE x = 't' AND y = 3">
        >>> 'WHERE x = ' + sqlquote(True) + ' AND y IN ' + sqlquote([2, 3])
        <sql: "WHERE x = 't' AND y IN (2, 3)">
    """
    from decimal import Decimal
    if isinstance(a, list):
        return _sqllist(a)
    elif isinstance(a, Decimal):
        return str(a)
    else:
        return sqlparam(a).sqlquery()

class Transaction:
    """Database transaction."""
    def __init__(self, ctx):
        self.ctx = ctx
        self.transaction_count = transaction_count = len(ctx.transactions)

        class transaction_engine:
            """Transaction Engine used in top level transactions."""
            def do_transact(self):
                ctx.commit(unload=False)

            def do_commit(self):
                ctx.commit()

            def do_rollback(self):
                ctx.rollback()

        class subtransaction_engine:
            """Transaction Engine used in sub transactions."""
            def query(self, q):
                db_cursor = ctx.db.cursor()
                ctx.db_execute(db_cursor, SQLQuery(q % transaction_count))

            def do_transact(self): # 20151224 jincw
                self.query('SAVE TRANSACTION webpy_sp_%s' if ctx.dbtype=='mssql' else 'SAVEPOINT webpy_sp_%s')

            def do_commit(self):
                if ctx.dbtype != 'mssql':
                    self.query('RELEASE SAVEPOINT webpy_sp_%s')

            def do_rollback(self):
                self.query('ROLLBACK TRANSACTION webpy_sp_%s' if ctx.dbtype=='mssql' else 'ROLLBACK TO SAVEPOINT webpy_sp_%s')

        class dummy_engine:
            """Transaction Engine used instead of subtransaction_engine
            when sub transactions are not supported."""
            do_transact = do_commit = do_rollback = lambda self: None

        if self.transaction_count:
            # nested transactions are not supported in some databases
            if self.ctx.get('ignore_nested_transactions'):
                self.engine = dummy_engine()
            else:
                self.engine = subtransaction_engine()
        else:
            self.engine = transaction_engine()

        self.engine.do_transact()
        self.ctx.transactions.append(self)

    def __enter__(self):
        return self

    def __exit__(self, exctype, excvalue, traceback):
        if exctype is not None:
            self.rollback()
        else:
            self.commit()

    def commit(self):
        if len(self.ctx.transactions) > self.transaction_count:
            self.engine.do_commit()
            self.ctx.transactions = self.ctx.transactions[:self.transaction_count]

    def rollback(self):
        if len(self.ctx.transactions) > self.transaction_count:
            self.engine.do_rollback()
            self.ctx.transactions = self.ctx.transactions[:self.transaction_count]

class DB:
    """Database"""
    def __init__(self, db_module, keywords):
        """Creates a database.
        """
        # some DB implementaions take optional paramater `driver` to use a specific driver modue
        # but it should not be passed to connect
        keywords.pop('driver', None)
        self.forcelower = keywords.pop('forcelower', False)

        self.db_module = db_module
        self.keywords = keywords

        self._ctx = threadeddict()
        # flag to enable/disable printing queries
        self.printing = config.get('debug_sql', config.get('debug', False))
        self.supports_multiple_insert = False

        self.cache_tables = []
        self.cacher = None
        self.isCacher = False

        try:
            import DBUtils
            # enable pooling if DBUtils module is available.
            self.has_pooling = True
        except ImportError:
            self.has_pooling = False

        # Pooling can be disabled by passing pooling=False in the keywords.
        self.has_pooling = self.keywords.pop('pooling', True) and self.has_pooling

    # def close(self):
    #     self.ctx.db.close()

    def _getctx(self):
        if not self._ctx.get('db'):
            self._load_context(self._ctx)
        return self._ctx
    ctx = property(_getctx)

    def _load_context(self, ctx):
        ctx.dbq_count = 0
        ctx.transactions = [] # stack of transactions
        ctx.dbtype = self.dbtype # 20151224 jincw

        if self.has_pooling:
            ctx.db = self._connect_with_pooling(self.keywords)
        else:
            ctx.db = self._connect(self.keywords)
        ctx.db_execute = self._db_execute

        if not hasattr(ctx.db, 'commit'):
            ctx.db.commit = lambda: None

        if not hasattr(ctx.db, 'rollback'):
            ctx.db.rollback = lambda: None

        def commit(unload=True):
            # do db commit and release the connection if pooling is enabled.
            ctx.db.commit()
            if unload and self.has_pooling:
                self._unload_context(self._ctx)

        def rollback():
            # do db rollback and release the connection if pooling is enabled.
            ctx.db.rollback()
            if self.has_pooling:
                self._unload_context(self._ctx)

        ctx.commit = commit
        ctx.rollback = rollback

    def _unload_context(self, ctx):
        del ctx.db

    def _connect(self, keywords):
        return self.db_module.connect(**keywords)

    def _connect_with_pooling(self, keywords):
        def get_pooled_db():
            from DBUtils import PooledDB

            # In DBUtils 0.9.3, `dbapi` argument is renamed as `creator`
            # see Bug#122112

            if PooledDB.__version__.split('.') < '0.9.3'.split('.'):
                return PooledDB.PooledDB(dbapi=self.db_module, **keywords)
            else:
                return PooledDB.PooledDB(creator=self.db_module, **keywords)

        if getattr(self, '_pooleddb', None) is None:
            self._pooleddb = get_pooled_db()

        return self._pooleddb.connection()

    def _db_cursor(self):
        return self.ctx.db.cursor()

    def _param_marker(self):
        """Returns parameter marker based on paramstyle attribute if this database."""
        style = getattr(self, 'paramstyle', 'pyformat')

        if style == 'qmark':
            return '?'
        elif style == 'numeric':
            return ':1'
        elif style in ('format', 'pyformat'):
            return '%s'
        raise UnknownParamstyle, style

    def _db_execute(self, cur, sql_query):
        """executes an sql query"""
        self.ctx.dbq_count += 1
        self.printing = config.get('debug_sql', config.get('debug', False)) #20140914 dongyg: set print debug information or not print
        try:
            a = time.time()
            query, params = self._process_query(sql_query)
            out = cur.execute(query, params)
            b = time.time()
        except:
            # if True and not self.isCacher:
            if True:
                s = str(sql_query)
                try:
                    s = s.decode('utf8') # 20151216 jincw
                except:
                    pass
                print >> debug, 'ERR:'+('Cacher:' if self.isCacher else ''), s[:1024] # Print SQL clause when the length of sql_query less than 1024 bytes.
            if self.ctx.transactions:
                self.ctx.transactions[-1].rollback()
            else:
                self.ctx.rollback()
            raise
        if self.printing and not self.isCacher:
        # if self.printing:
            s = str(sql_query)
            try:
                s = s.decode('utf8') # 20151216 jincw
            except:
                pass
            if s.find(" sessions ")<0: #20140914 dongyg: the table [sessions] not print
                print >> debug, ('Cacher:' if self.isCacher else '')+'%s (%s): %s' % (round(b-a, 2), self.ctx.dbq_count, s)
        return out

    def _process_query(self, sql_query):
        """Takes the SQLQuery object and returns query string and parameters.
        """
        paramstyle = getattr(self, 'paramstyle', 'pyformat')
        query = sql_query.query(paramstyle)
        params = sql_query.values()
        return query, params

    def _where(self, where, vars):
        if isinstance(where, (int, long)):
            where = "id = " + sqlparam(where)
        #@@@ for backward-compatibility
        elif isinstance(where, (list, tuple)) and len(where) == 2:
            where = SQLQuery(where[0], where[1])
        elif isinstance(where, SQLQuery):
            pass
        else:
            where = reparam(where, vars)
        return where

    def query(self, sql_query, vars=None, processed=False, _test=False, forcelower=True, no_tran=False):
        """
        Execute SQL query `sql_query` using dictionary `vars` to interpolate it.
        If `processed=True`, `vars` is a `reparam`-style list to use
        instead of interpolating.

            >>> db = DB(None, {})
            >>> db.query("SELECT * FROM foo", _test=True)
            <sql: 'SELECT * FROM foo'>
            >>> db.query("SELECT * FROM foo WHERE x = $x", vars=dict(x='f'), _test=True)
            <sql: "SELECT * FROM foo WHERE x = 'f'">
            >>> db.query("SELECT * FROM foo WHERE x = " + sqlquote('f'), _test=True)
            <sql: "SELECT * FROM foo WHERE x = 'f'">
        """
        if vars is None: vars = {}

        if not processed and not isinstance(sql_query, SQLQuery):
            sql_query = reparam(sql_query, vars)

        if _test: return sql_query

        db_cursor = self._db_cursor()
        self._db_execute(db_cursor, sql_query)

        if db_cursor.description:
            if self.dbtype=='oracle' and self.forcelower and forcelower: #20150126 dongyg: Oracle TableName/FieldName convert to lowercase
                names = [x[0].lower() for x in db_cursor.description]
            else:
                names = [x[0] for x in db_cursor.description]
            # 20151014 jincw: fix the problem of "db_cursor.rowcount is -1" in pymssql
            #   Cursor.rowcount (http://www.pymssql.org/en/latest/ref/pymssql.html#cursor-class)
            #       Returns number of rows affected by last operation. In case of SELECT statements it returns meaningful information only after all rows have been fetched.
            if self.dbtype=='mssql':
                from collections import deque
                Q = deque(db_cursor.fetchall())
                gen = (storage(zip(names, Q.popleft())) for i in xrange(len(Q)))
                out = iterbetter(gen)
                out.list = lambda: list(gen)
            else:
                def iterwrapper():
                    row = db_cursor.fetchone()
                    while row:
                        yield storage(zip(names, row)) # yield storage(dict(zip(names, row))) #jincw 20151021
                        row = db_cursor.fetchone()
                out = iterbetter(iterwrapper())
                out.list = lambda: [storage(zip(names, x)) \
                                   for x in db_cursor.fetchall()]
            if self.dbtype=='sqlite':
                out.__len__ = lambda: len(db_cursor.fetchall())
            else:
                out.__len__ = lambda: int(db_cursor.rowcount)
        else:
            out = db_cursor.rowcount

        # 针对 调用查询类的mysql存储过程后再commit会报out of sync异常 的问题，加no_tran参数
        if not self.ctx.transactions and not no_tran:
            self.ctx.commit()
        return out

    def select(self, tables, vars=None, what='*', where=None, order=None, group=None,
               limit=None, offset=None, _test=False):
        """
        Selects `what` from `tables` with clauses `where`, `order`,
        `group`, `limit`, and `offset`. Uses vars to interpolate.
        Otherwise, each clause can be a SQLQuery.

            >>> db = DB(None, {})
            >>> db.select('foo', _test=True)
            <sql: 'SELECT * FROM foo'>
            >>> db.select(['foo', 'bar'], where="foo.bar_id = bar.id", limit=5, _test=True)
            <sql: 'SELECT * FROM foo, bar WHERE foo.bar_id = bar.id LIMIT 5'>
        """
        #20160720 dongyg 添加缓存处理
        if self.cacher and self.isAllCached(tables) and not _test:
            return self.cacher.db.select(tables, vars, what, where, order, group, limit, offset, _test)
        #
        if vars is None: vars = {}
        li_sql_clauses = self.sql_clauses(what, tables, where, group, order, limit, offset)
        clauses = [self.gen_clause(sql, val, vars) for sql, val in li_sql_clauses if val is not None]
        qout = SQLQuery.join(clauses)
        if _test: return qout
        return self.query(qout, processed=True)

    def where(self, table, what='*', order=None, group=None, limit=None,
              offset=None, _test=False, **kwargs):
        """
        Selects from `table` where keys are equal to values in `kwargs`.

            >>> db = DB(None, {})
            >>> db.where('foo', bar_id=3, _test=True)
            <sql: 'SELECT * FROM foo WHERE bar_id = 3'>
            >>> db.where('foo', source=2, crust='dewey', _test=True)
            <sql: "SELECT * FROM foo WHERE source = 2 AND crust = 'dewey'">
            >>> db.where('foo', _test=True)
            <sql: 'SELECT * FROM foo'>
        """
        where_clauses = []
        for k, v in kwargs.iteritems():
            where_clauses.append(k + ' = ' + sqlquote(v))

        if where_clauses:
            where = SQLQuery.join(where_clauses, " AND ")
        else:
            where = None

        return self.select(table, what=what, order=order,
               group=group, limit=limit, offset=offset, _test=_test,
               where=where)

    def sql_clauses(self, what, tables, where, group, order, limit, offset):
        return (
            ('SELECT', what),
            ('FROM', sqllist(tables)),
            ('WHERE', where),
            ('GROUP BY', group),
            ('ORDER BY', order),
            ('LIMIT', limit),
            ('OFFSET', offset))

    def gen_clause(self, sql, val, vars):
        if isinstance(val, (int, long)):
            if sql == 'WHERE':
                nout = 'id = ' + sqlquote(val)
            else:
                nout = SQLQuery(val)
        #@@@
        elif isinstance(val, (list, tuple)) and len(val) == 2:
            nout = SQLQuery(val[0], val[1]) # backwards-compatibility
        elif isinstance(val, SQLQuery):
            nout = val
        else:
            nout = reparam(val, vars)

        def xjoin(a, b):
            if a and b: return a + ' ' + b
            else: return a or b

        return xjoin(sql, nout)

    def insert(self, tablename, seqname=None, _test=False, **values):
        """
        Inserts `values` into `tablename`. Returns current sequence ID.
        Set `seqname` to the ID if it's not the default, or to `False`
        if there isn't one.

            >>> db = DB(None, {})
            >>> q = db.insert('foo', name='bob', age=2, created=SQLLiteral('NOW()'), _test=True)
            >>> q
            <sql: "INSERT INTO foo (age, name, created) VALUES (2, 'bob', NOW())">
            >>> q.query()
            'INSERT INTO foo (age, name, created) VALUES (%s, %s, NOW())'
            >>> q.values()
            [2, 'bob']
        """
        def q(x): return "(" + x + ")"

        if values:
            _keys = SQLQuery.join(values.keys(), ', ')
            _values = SQLQuery.join([sqlparam(v) for v in values.values()], ', ')
            sql_query = "INSERT INTO %s " % tablename + q(_keys) + ' VALUES ' + q(_values)
        else:
            sql_query = SQLQuery(self._get_insert_default_values_query(tablename))

        if _test: return sql_query

        db_cursor = self._db_cursor()
        if seqname is not False:
            sql_query = self._process_insert_query(sql_query, tablename, seqname)

        if isinstance(sql_query, tuple):
            # for some databases, a separate query has to be made to find
            # the id of the inserted row.
            q1, q2 = sql_query
            self._db_execute(db_cursor, q1)
            self._db_execute(db_cursor, q2)
        else:
            self._db_execute(db_cursor, sql_query)

        out = None
        try:
            out = db_cursor.fetchone()[0]
        except Exception:
            pass
        # jincw 2016-05-11: 解决sql server在insert后拿不到自增主键的值的问题
        if out is None:
            try:
                out = db_cursor.lastrowid
            except:
                pass
        from decimal import Decimal
        if isinstance(out, Decimal):
            out = int(out)

        if not self.ctx.transactions:
            self.ctx.commit()
        #20160720 dongyg 添加缓存处理
        if self.cacher and self.isAllCached(tablename) and not _test:
            try:
                self.cacher.db.insert(tablename, seqname, _test, **values)
            except Exception, e:
                self.cacheTables(tablename)
        #
        return out

    def _get_insert_default_values_query(self, table):
        return "INSERT INTO %s DEFAULT VALUES" % table

    def multiple_insert(self, tablename, values, seqname=None, _test=False):
        """
        Inserts multiple rows into `tablename`. The `values` must be a list of dictioanries,
        one for each row to be inserted, each with the same set of keys.
        Returns the list of ids of the inserted rows.
        Set `seqname` to the ID if it's not the default, or to `False`
        if there isn't one.

            >>> db = DB(None, {})
            >>> db.supports_multiple_insert = True
            >>> values = [{"name": "foo", "email": "foo@example.com"}, {"name": "bar", "email": "bar@example.com"}]
            >>> db.multiple_insert('person', values=values, _test=True)
            <sql: "INSERT INTO person (name, email) VALUES ('foo', 'foo@example.com'), ('bar', 'bar@example.com')">
        """
        if not values:
            return []

        if not self.supports_multiple_insert:
            out = [self.insert(tablename, seqname=seqname, _test=_test, **v) for v in values]
            if seqname is False:
                return None
            else:
                return out

        keys = values[0].keys()
        #@@ make sure all keys are valid

        # make sure all rows have same keys.
        for v in values:
            if v.keys() != keys:
                raise ValueError, 'Bad data'

        sql_query = SQLQuery('INSERT INTO %s (%s) VALUES ' % (tablename, ', '.join(keys)))

        for i, row in enumerate(values):
            if i != 0:
                sql_query.append(", ")
            SQLQuery.join([SQLParam(row[k]) for k in keys], sep=", ", target=sql_query, prefix="(", suffix=")")

        if _test: return sql_query

        db_cursor = self._db_cursor()
        if seqname is not False:
            sql_query = self._process_insert_query(sql_query, tablename, seqname)

        if isinstance(sql_query, tuple):
            # for some databases, a separate query has to be made to find
            # the id of the inserted row.
            q1, q2 = sql_query
            self._db_execute(db_cursor, q1)
            self._db_execute(db_cursor, q2)
        else:
            self._db_execute(db_cursor, sql_query)

        try:
            out = db_cursor.fetchone()[0]
            out = range(out-len(values)+1, out+1)
        except Exception:
            out = None

        if not self.ctx.transactions:
            self.ctx.commit()
        #20160720 dongyg 添加缓存处理
        if self.cacher and self.isAllCached(tablename) and not _test: #缓存数据库不支持批量插入，得一条条插
            # [self.cacher.db.insert(tablename, seqname=seqname, _test=_test, **v) for v in values]
            self.cacheTables(tablename) #重新缓存
        #
        return out


    def update(self, tables, where, vars=None, _test=False, **values):
        """
        Update `tables` with clause `where` (interpolated using `vars`)
        and setting `values`.

            >>> db = DB(None, {})
            >>> name = 'Joseph'
            >>> q = db.update('foo', where='name = $name', name='bob', age=2,
            ...     created=SQLLiteral('NOW()'), vars=locals(), _test=True)
            >>> q
            <sql: "UPDATE foo SET age = 2, name = 'bob', created = NOW() WHERE name = 'Joseph'">
            >>> q.query()
            'UPDATE foo SET age = %s, name = %s, created = NOW() WHERE name = %s'
            >>> q.values()
            [2, 'bob', 'Joseph']
        """
        if vars is None: vars = {}
        where = self._where(where, vars)

        query = (
          "UPDATE " + sqllist(tables) +
          " SET " + sqlwhere(values, ', ') +
          " WHERE " + where)

        if _test: return query

        db_cursor = self._db_cursor()
        self._db_execute(db_cursor, query)
        if not self.ctx.transactions:
            self.ctx.commit()
        #20160720 dongyg 添加缓存处理
        if self.cacher and self.isAllCached(tables) and not _test:
            try:
                self.cacher.db.update(tables, where, vars, _test, **values)
            except Exception, e:
                self.cacheTables(tablename)
        #
        return db_cursor.rowcount

    def delete(self, table, where, using=None, vars=None, _test=False):
        """
        Deletes from `table` with clauses `where` and `using`.

            >>> db = DB(None, {})
            >>> name = 'Joe'
            >>> db.delete('foo', where='name = $name', vars=locals(), _test=True)
            <sql: "DELETE FROM foo WHERE name = 'Joe'">
        """
        if vars is None: vars = {}
        where = self._where(where, vars)

        q = 'DELETE FROM ' + table
        if using: q += ' USING ' + sqllist(using)
        if where: q += ' WHERE ' + where

        if _test: return q

        db_cursor = self._db_cursor()
        self._db_execute(db_cursor, q)
        if not self.ctx.transactions:
            self.ctx.commit()
        #20160720 dongyg 添加缓存处理
        if self.cacher and self.isAllCached(table) and not _test:
            try:
                self.cacher.db.delete(table, where, using, vars, _test)
            except Exception, e:
                self.cacheTables(tablename)
        #
        return db_cursor.rowcount

    def _process_insert_query(self, query, tablename, seqname):
        return query

    def transaction(self):
        """Start a transaction."""
        return Transaction(self.ctx)

    # 20160720 dongyg 添加缓存功能
    def cacheTables(self,tables):
        '''缓存表指定表: ''或[]'''
        if not self.cacher: return []
        retval = self.cacher.cacheTables(self,tables)
        self.cache_tables = list(set(self.cache_tables+retval))
    def isAllCached(self,tables):
        '''判断表是否已缓存: ''或[]'''
        if isinstance(tables, basestring):
            if tables.find(' on')>0:
                tables = tables[:tables.find(' on')]
            if tables.find('left join')>0:
                tables = tables.replace('left join',',')
            if tables.find('right join')>0:
                tables = tables.replace('right join',',')
            if tables.find('join')>0:
                tables = tables.replace('join',',')
            tables = tables.split(',')
        tables = [x.strip() for x in tables]
        target_tables = dict([(x.split(' ')[len(x.split(' '))-1],x.split(' ')[0]) for x in tables])
        nocache = set(target_tables.values()) - set(self.cache_tables)
        return not bool(nocache)
    def cacheSchema(self):
        '''缓存数据库表结构。包含的表、字段。可为Fruit判定表或字段是否存在用。'''
        self.schema_fields = {}
        self.schema_tables = []
    def table_exists(self,tbname,tbowner=''):
        '''判断表是否存在'''
        pass
    def field_exists(self,tbname,fname):
        '''判断字段是否存在'''
        pass
    def list_fields(self,tbname):
        '''列出指定表的所有字段'''
        return []

class PostgresDB(DB):
    """Postgres driver."""
    def __init__(self, **keywords):
        if 'pw' in keywords:
            keywords['password'] = keywords.pop('pw')

        db_module = import_driver(["psycopg2", "psycopg", "pgdb"], preferred=keywords.pop('driver', None))
        if db_module.__name__ == "psycopg2":
            import psycopg2.extensions
            psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)

        # if db is not provided postgres driver will take it from PGDATABASE environment variable
        if 'db' in keywords:
            keywords['database'] = keywords.pop('db')

        self.dbname = keywords['database']
        self.dbtype = "postgres"
        self.paramstyle = db_module.paramstyle
        DB.__init__(self, db_module, keywords)
        self.supports_multiple_insert = True
        self._sequences = None

    def _process_insert_query(self, query, tablename, seqname):
        if seqname is None:
            # when seqname is not provided guess the seqname and make sure it exists
            seqname = tablename + "_id_seq"
            if seqname not in self._get_all_sequences():
                seqname = None

        if seqname:
            query += "; SELECT currval('%s')" % seqname

        return query

    def _get_all_sequences(self):
        """Query postgres to find names of all sequences used in this database."""
        if self._sequences is None:
            q = "SELECT c.relname FROM pg_class c WHERE c.relkind = 'S'"
            self._sequences = set([c.relname for c in self.query(q)])
        return self._sequences

    def _connect(self, keywords):
        conn = DB._connect(self, keywords)
        try:
            conn.set_client_encoding('UTF8')
        except AttributeError:
            # fallback for pgdb driver
            conn.cursor().execute("set client_encoding to 'UTF-8'")
        return conn

    def _connect_with_pooling(self, keywords):
        conn = DB._connect_with_pooling(self, keywords)
        conn._con._con.set_client_encoding('UTF8')
        return conn

class MySQLDB(DB):
    def __init__(self, **keywords):
        import MySQLdb as db
        if 'pw' in keywords:
            keywords['passwd'] = keywords['pw']
            del keywords['pw']

        if 'charset' not in keywords:
            keywords['charset'] = 'utf8'
        elif keywords['charset'] is None:
            del keywords['charset']

        self.paramstyle = db.paramstyle = 'pyformat' # it's both, like psycopg
        self.dbname = keywords['db']
        self.dbtype = "mysql"
        DB.__init__(self, db, keywords)
        self.supports_multiple_insert = True

    def _process_insert_query(self, query, tablename, seqname):
        return query, SQLQuery('SELECT last_insert_id();')

    def _get_insert_default_values_query(self, table):
        return "INSERT INTO %s () VALUES()" % table

    def execScriptFile(self,filename):
        '''执行sql脚本文件'''
        import os
        if not os.path.isfile(filename):
            raise Exception('File %s not found!'%filename)
        retval = callShell('mysql -V') #先检查mysql命令行是否可工作
        if not retval.startswith('mysql'):
            raise Exception('Shell mysql is not found.\n%s'%retval)
        return callShell('mysql -u%s -p%s -D%s < %s --default-character-set=utf8'%(self.keywords['user'],self.keywords['passwd'],self.dbname,filename))
    def cacheSchema(self):
        '''缓存数据库表结构。包含的表、字段。可为Fruit判定表或字段是否存在用。'''
        #mysql当连接数据库用户无权访问表时，就查不到这个表名
        dbname = self.dbname
        # self.schema_tables = [x.TABLE_NAME.upper() for x in self.select('INFORMATION_SCHEMA.TABLES', what='TABLE_NAME', vars=locals(), where="TABLE_SCHEMA=$dbname").list()]
        # self.schema_fields = [x.TABLE_NAME.upper()+'.'+x.COLUMN_NAME.upper() for x in self.select('INFORMATION_SCHEMA.COLUMNS', what='TABLE_NAME,COLUMN_NAME', vars=locals(), where="TABLE_SCHEMA=$dbname").list()]
        self.schema_fields = {}
        for x in self.select('INFORMATION_SCHEMA.COLUMNS', what='TABLE_NAME,COLUMN_NAME', vars=locals(), where="TABLE_SCHEMA=$dbname"):
            tbname, fname = x.TABLE_NAME.upper(), x.COLUMN_NAME.upper()
            if tbname in self.schema_fields:
                self.schema_fields[tbname].add(fname)
            else:
                self.schema_fields[tbname] = {fname}
        self.schema_tables = self.schema_fields.keys()

    def table_exists(self,tbname,tbowner=''):
        '''判断表是否存在'''
        # return tbname.upper() in self.schema_tables
        return tbname.upper() in self.schema_fields
    def field_exists(self,tbname,fname):
        '''判断字段是否存在'''
        # return tbname.upper()+'.'+fname.upper() in self.schema_fields
        tbname = tbname.upper()
        return tbname in self.schema_fields and fname.upper() in self.schema_fields[tbname]
    def list_fields(self,tbname):
        '''列出指定表的所有字段'''
        return list(self.schema_fields.get(tbname.upper(),set()))

def import_driver(drivers, preferred=None):
    """Import the first available driver or preferred driver.
    """
    if preferred:
        drivers = [preferred]

    for d in drivers:
        try:
            return __import__(d, None, None, ['x'])
        except ImportError:
            pass
    raise ImportError("Unable to import " + " or ".join(drivers))

class SqliteDB(DB):
    def __init__(self, **keywords):
        db = import_driver(["sqlite3", "pysqlite2.dbapi2", "sqlite"], preferred=keywords.pop('driver', None))

        if db.__name__ in ["sqlite3", "pysqlite2.dbapi2"]:
            db.paramstyle = 'qmark'

        # sqlite driver doesn't create datatime objects for timestamp columns unless `detect_types` option is passed.
        # It seems to be supported in sqlite3 and pysqlite2 drivers, not surte about sqlite.
        keywords.setdefault('detect_types', db.PARSE_DECLTYPES)

        self.paramstyle = db.paramstyle
        keywords['database'] = keywords.pop('db')
        keywords['pooling'] = False # sqlite don't allows connections to be shared by threads
        self.dbname = keywords['database']
        self.dbtype = "sqlite"
        DB.__init__(self, db, keywords)

    def _process_insert_query(self, query, tablename, seqname):
        return query, SQLQuery('SELECT last_insert_rowid();')

    def query(self, *a, **kw):
        out = DB.query(self, *a, **kw)
        # if isinstance(out, iterbetter):
        #     del out.__len__
        return out

    def _connect(self, keywords):
        conn = DB._connect(self, keywords)
        # use 8-bit strings instead of unicode string in sqlite3, set approptiate text_factory for sqlite connection
        conn.text_factory = str
        return conn

    def _connect_with_pooling(self, keywords):
        conn = DB._connect_with_pooling(self, keywords)
        conn.text_factory = str
        return conn

    def execScriptFile(self,filename):
        '''执行sql脚本文件'''
        import os
        if not os.path.isfile(filename):
            raise Exception('File %s not found!'%filename)
        file_object = open(filename)
        try:
            all_the_text = file_object.read()
        finally:
            file_object.close()
        retval = ''
        t = self.transaction()
        try:
            out = self._db_cursor().executescript(all_the_text)
        except Exception, e:
            t.rollback()
            import traceback
            traceback.print_exc()
            retval = e
            raise e
        else:
            t.commit()
        return retval

    def cacheSchema(self):
        '''缓存数据库表结构。包含的表、字段。可为Fruit判定表或字段是否存在用。'''
        self.schema_fields = {}
        for tb in self.query("select * from sqlite_master WHERE type = 'table'").list():
            self.schema_fields[tb.tbl_name.upper()] = set([x.name.upper() for x in self.query("PRAGMA table_info(%s)"%tb.tbl_name).list()])
        self.schema_tables = list(self.schema_fields.iterkeys())
    def table_exists(self,tbname,tbowner=''):
        '''判断表是否存在'''
        return tbname.upper() in self.schema_fields
    def field_exists(self,tbname,fname):
        '''判断字段是否存在'''
        tbname = tbname.upper()
        return tbname in self.schema_fields and fname.upper() in self.schema_fields[tbname]
    def list_fields(self,tbname):
        '''列出指定表的所有字段'''
        return list(self.schema_fields.get(tbname.upper(),set()))

class FirebirdDB(DB):
    """Firebird Database.
    """
    def __init__(self, **keywords):
        try:
            import kinterbasdb as db
        except Exception:
            db = None
            pass
        if 'pw' in keywords:
            keywords['passwd'] = keywords['pw']
            del keywords['pw']
        keywords['database'] = keywords['db']
        del keywords['db']
        self.dbtype = "firebird"
        DB.__init__(self, db, keywords)

    def delete(self, table, where=None, using=None, vars=None, _test=False):
        # firebird doesn't support using clause
        using=None
        return DB.delete(self, table, where, using, vars, _test)

    def sql_clauses(self, what, tables, where, group, order, limit, offset):
        return (
            ('SELECT', ''),
            ('FIRST', limit),
            ('SKIP', offset),
            ('', what),
            ('FROM', sqllist(tables)),
            ('WHERE', where),
            ('GROUP BY', group),
            ('ORDER BY', order)
        )

class MSSQLDB(DB):
    def __init__(self, **keywords):
        import pymssql as db
        if 'pw' in keywords:
            keywords['password'] = keywords.pop('pw')
        keywords['database'] = keywords.pop('db')
        self.dbname = keywords['database']
        self.dbtype = "mssql"
        DB.__init__(self, db, keywords)

    def _process_query(self, sql_query):
        """Takes the SQLQuery object and returns query string and parameters.
        """
        # MSSQLDB expects params to be a tuple.
        # Overwriting the default implementation to convert params to tuple.
        paramstyle = getattr(self, 'paramstyle', 'pyformat')
        query = sql_query.query(paramstyle)
        params = sql_query.values()
        return query, tuple(params)

    def sql_clauses(self, what, tables, where, group, order, limit, offset):
        # 20150127 dongyg: MSSQL does not support LIMIT/OFFSET keywords, use 'row_number()' replaces it like follow:
        # SELECT * FROM (SELECT ROW_NUMBER() OVER(ORDER BY menu_code desc) rownum, menu_code,menu_name FROM org_menu group by menu_code,menu_name) r WHERE r.rownum BETWEEN 5 AND 10
        if limit or offset:
            if not offset: offset = 0
            return (
                ('SELECT', '* FROM (SELECT ROW_NUMBER() OVER('),
                ('ORDER BY', order),
                (') rownum,', what),
                ('FROM', sqllist(tables)),
                ('WHERE', where),
                ('GROUP BY', group),
                (') r', ''),
                ('WHERE','r.rownum'),
                ('BETWEEN',offset+1),
                ('AND',offset+limit)
            )
        else:
            return DB.sql_clauses(self, what, tables, where, group, order, limit, offset)

    def _test(self):
        """Test LIMIT.

            Fake presence of pymssql module for running tests.
            >>> import sys
            >>> sys.modules['pymssql'] = sys.modules['sys']

            MSSQL has TOP clause instead of LIMIT clause.
            >>> db = MSSQLDB(db='test', user='joe', pw='secret')
            >>> db.select('foo', limit=4, _test=True)
            <sql: 'SELECT TOP 4 * FROM foo'>
        """
        pass

    def execScriptFile(self,filename):
        '''执行sql脚本文件。sqlcmd/osql都必须用gbk编码的文件，utf8编码的文件的话会出奇怪的错误'''
        import os
        if not os.path.isfile(filename):
            raise Exception('File %s not found!'%filename)
        retval = callShell('sqlcmd /?') #先检查sqlcmd命令行是否可工作
        if not retval.startswith('Microsoft'):
            raise Exception('Shell sqlcmd is not found.\n%s'%retval)
        return callShell('sqlcmd -S %s,%s -U%s -P%s -d %s -i %s'%(self.keywords['host'],self.keywords['port'],self.keywords['user'],self.keywords['password'],self.dbname,filename))
    def cacheSchema(self):
        '''缓存数据库表结构。包含的表、字段。可为Fruit判定表或字段是否存在用。'''
        # self.schema_tables = {x.TABLE_NAME.upper() for x in self.select('sys.all_objects', what='name as TABLE_NAME', vars=locals(), where="type in ('U','V')")}
        # self.schema_fields = {x.TABLE_NAME.upper()+'.'+x.COLUMN_NAME.upper() for x in self.select("sys.all_columns c,sys.all_objects o",
        #                             where="c.object_id=o.object_id and o.type in ('U','V')",what="o.name TABLE_NAME,c.name COLUMN_NAME")}
        self.schema_fields = {}
        for x in self.select("sys.all_columns c,sys.all_objects o",
                                    where="c.object_id=o.object_id and o.type in ('U','V')",what="o.name TABLE_NAME,c.name COLUMN_NAME"):
            tbname, fname = x.TABLE_NAME.upper(), x.COLUMN_NAME.upper()
            if tbname in self.schema_fields:
                self.schema_fields[tbname].add(fname)
            else:
                self.schema_fields[tbname] = {fname}
        self.schema_tables = self.schema_fields.keys()
    def table_exists(self,tbname,tbowner=''):
        '''判断表是否存在'''
        # return tbname.upper() in self.schema_tables
        return tbname.upper() in self.schema_fields
    def field_exists(self,tbname,fname):
        '''判断字段是否存在'''
        # return tbname.upper()+'.'+fname.upper() in self.schema_fields
        tbname = tbname.upper()
        return tbname in self.schema_fields and fname.upper() in self.schema_fields[tbname]
    def list_fields(self,tbname):
        '''列出指定表的所有字段'''
        return list(self.schema_fields.get(tbname.upper(),set()))

class OracleDB(DB):
    def __init__(self, **keywords):
        import cx_Oracle as db
        if 'pw' in keywords:
            keywords['password'] = keywords.pop('pw')

        #@@ TODO: use db.makedsn if host, port is specified
        keywords['dsn'] = keywords.pop('db')
        self.dbname = keywords['dsn']
        self.dbtype = 'oracle'
        self.user = keywords['user']
        db.paramstyle = 'numeric'
        self.paramstyle = db.paramstyle

        # oracle doesn't support pooling
        keywords.pop('pooling', None)
        DB.__init__(self, db, keywords)

    def _process_insert_query(self, query, tablename, seqname):
        if seqname is None:
            # It is not possible to get seq name from table name in Oracle
            return query
        else:
            return query + "; SELECT %s.currval FROM dual" % seqname

    def sql_clauses(self, what, tables, where, group, order, limit, offset):
        # 20150127 dongyg: Oracle does not support LIMIT/OFFSET keywords, use 'rownum' replaces it like follow:
        # select * from (select * from (select rownum r1,t.* from (select * from org_menu order by menu_code desc) t) where rownum<=8) where r1>4
        if limit or offset:
            if not offset: offset = 0
            return (
                ("select * from (select * from (select rownum r1,t.* from (",""),
                ('SELECT', what),
                ('FROM', sqllist(tables)),
                ('WHERE', where),
                ('GROUP BY', group),
                ('ORDER BY', order),
                (') t) where rownum<=', offset+limit),
                (') where r1>', offset)
            )
        else:
            return DB.sql_clauses(self, what, tables, where, group, order, limit, offset)

    def execScriptFile(self,filename):
        '''执行sql脚本文件'''
        import os
        if not os.path.isfile(filename):
            raise Exception('File %s not found!'%filename)
        print 'It is not implement to execute SQL Script on Oracle. Please execute it manually.'
    def cacheSchema(self):
        '''缓存数据库表结构。包含的表、字段。可为Fruit判定表或字段是否存在用。'''
        self.schema_tables = [x.owner.upper()+'.'+x.table_name.upper() for x in self.select("all_tables",what="OWNER,TABLE_NAME").list()]
        self.schema_tables = self.schema_tables+[x.owner.upper()+'.'+x.table_name.upper() for x in self.select("all_views",what="OWNER,VIEW_NAME TABLE_NAME").list()]
        self.schema_tables = self.schema_tables+['.'+x.table_name.upper() for x in self.select("user_tables",what="TABLE_NAME").list()]
        self.schema_tables = self.schema_tables+['.'+x.table_name.upper() for x in self.select("user_views",what="VIEW_NAME TABLE_NAME").list()]
        self.schema_fields = [x.table_name.upper()+'.'+x.column_name.upper() for x in self.select("all_tab_columns",what="TABLE_NAME,COLUMN_NAME").list()]
    def table_exists(self,tbname,tbowner=''):
        '''判断表是否存在'''
        #当连接数据库用户不是表属主时需要判断属主
        return tbowner.upper()+'.'+tbname.upper() in self.schema_tables
    def field_exists(self,tbname,fname):
        '''判断字段是否存在'''
        return tbname.upper()+'.'+fname.upper() in self.schema_fields
    def list_fields(self,tbname):
        '''列出指定表的所有字段'''
        tbname = tbname.upper() + '.'
        prefix_len = len(tbname)
        return [x[prefix_len:] for x in self.schema_fields if x.startswith(tbname)]

_databases = {}
def database(dburl=None, **params):
    """Creates appropriate database using params.

    Pooling will be enabled if DBUtils module is available.
    Pooling can be disabled by passing pooling=False in params.
    """
    dbn = params.pop('dbn')
    if dbn in _databases:
        return _databases[dbn](**params)
    else:
        raise UnknownDB, dbn

def register_database(name, clazz):
    """
    Register a database.

        >>> class LegacyDB(DB):
        ...     def __init__(self, **params):
        ...        pass
        ...
        >>> register_database('legacy', LegacyDB)
        >>> db = database(dbn='legacy', db='test', user='joe', passwd='secret')
    """
    _databases[name] = clazz

register_database('mysql', MySQLDB)
register_database('postgres', PostgresDB)
register_database('sqlite', SqliteDB)
register_database('firebird', FirebirdDB)
register_database('mssql', MSSQLDB)
register_database('oracle', OracleDB)

def _interpolate(format):
    """
    Takes a format string and returns a list of 2-tuples of the form
    (boolean, string) where boolean says whether string should be evaled
    or not.

    from <http://lfw.org/python/Itpl.py> (public domain, Ka-Ping Yee)
    """
    from tokenize import tokenprog

    def matchorfail(text, pos):
        match = tokenprog.match(text, pos)
        if match is None:
            raise _ItplError(text, pos)
        return match, match.end()

    namechars = "abcdefghijklmnopqrstuvwxyz" \
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_";
    chunks = []
    pos = 0

    while 1:
        dollar = format.find("$", pos)
        if dollar < 0:
            break
        nextchar = format[dollar + 1]

        if nextchar == "{":
            chunks.append((0, format[pos:dollar]))
            pos, level = dollar + 2, 1
            while level:
                match, pos = matchorfail(format, pos)
                tstart, tend = match.regs[3]
                token = format[tstart:tend]
                if token == "{":
                    level = level + 1
                elif token == "}":
                    level = level - 1
            chunks.append((1, format[dollar + 2:pos - 1]))

        elif nextchar in namechars:
            chunks.append((0, format[pos:dollar]))
            match, pos = matchorfail(format, dollar + 1)
            while pos < len(format):
                if format[pos] == "." and \
                    pos + 1 < len(format) and format[pos + 1] in namechars:
                    match, pos = matchorfail(format, pos + 1)
                elif format[pos] in "([":
                    pos, level = pos + 1, 1
                    while level:
                        match, pos = matchorfail(format, pos)
                        tstart, tend = match.regs[3]
                        token = format[tstart:tend]
                        if token[0] in "([":
                            level = level + 1
                        elif token[0] in ")]":
                            level = level - 1
                else:
                    break
            chunks.append((1, format[dollar + 1:pos]))
        else:
            chunks.append((0, format[pos:dollar + 1]))
            pos = dollar + 1 + (nextchar == "$")

    if pos < len(format):
        chunks.append((0, format[pos:]))
    return chunks

if __name__ == "__main__":
    import doctest
    doctest.testmod()
