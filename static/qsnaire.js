var format = function(fmt) {
    if (typeof fmt !== 'string') {
        throw {name: 'FormatStringError', message: 'NEED a Format String!'};
    } else if (! /^(%([%shjnb]|\d*d)|[^%])*$/.test(fmt)) {
        throw {name: 'FormatStringError', message: js(fmt)+' not proper'};
    }
    var idx = 1, args = arguments;
    return fmt.replace(/%([%shjnb]|(\d*)d)/g, function(match, f, w) {
        // console.log('match: '+match);
        // console.log('f: '+f);
        // console.log('w: '+w);
        if (f === '%') {
            return '%';
        }
        if (idx >= args.length) {
            return match; //
        }
        var arg = args[idx];
        idx ++;
        if (f === 's') {
            return '' + arg; //arg.toString();
        } else if (f === 'h') {
            return htmlEscape(''+arg);
        } else if (f === 'j') {
            return js(arg);
        } else if (f === 'n') {
            return '' + arg;
        } else if (f === 'b') {
            return arg? 'true': 'false';
        } else { // \d*d
            var s = '' + arg.toFixed(0);
            if (! w) {
                return s;
            }
            var padding = w.length>1 && w.charAt(0)=='0'? '0': ' ';
            var width = parseInt(w, 10);
            while (s.length < width) {
                s = padding + s;
            }
            return s;
        }
    });
}
function getFullDateTime(d) {
    //得到yyyy-mm-dd hh:nn形式日期时间字符串
    d = d || new Date();
    return format('%04d-%02d-%02d %02d:%02d', d.getFullYear(), d.getMonth()+1,
                  d.getDate(), d.getHours(), d.getMinutes());
}
function getFullDateTime1(d) {
    //得到yyyy-mm-dd hh:nn:ss形式日期时间字符串
    d = d || new Date();
    return format('%04d-%02d-%02d %02d:%02d:%02d', d.getFullYear(), d.getMonth()+1,
                  d.getDate(), d.getHours(), d.getMinutes(), d.getSeconds());
}
function get_yyyy_mm_dd(d) {
    //得到yyyy-mm-dd形式日期字符串
    d = d || new Date();
    return format('%04d-%02d-%02d', d.getFullYear(), d.getMonth()+1, d.getDate());
}

var formatJson = function(json, options) {
    var reg = null,
        formatted = '',
        pad = 0,
        PADDING = '    '; // one can also use '\t' or a different number of spaces

    // optional settings
    options = options || {};
    // remove newline where '{' or '[' follows ':'
    options.newlineAfterColonIfBeforeBraceOrBracket = (options.newlineAfterColonIfBeforeBraceOrBracket === true) ? true : false;
    // use a space after a colon
    options.spaceAfterColon = (options.spaceAfterColon === false) ? false : true;

    // begin formatting...
    if (typeof json !== 'string') {
        // make sure we start with the JSON as a string
        json = JSON.stringify(json);
    } else {
        // is already a string, so parse and re-stringify in order to remove extra whitespace
        json = JSON.parse(json);
        json = JSON.stringify(json);
    }

    // add newline before and after curly braces
    reg = /([\{\}])/g;
    json = json.replace(reg, '\r\n$1\r\n');

    // add newline before and after square brackets
    reg = /([\[\]])/g;
    json = json.replace(reg, '\r\n$1\r\n');

    // add newline after comma
    reg = /(\,)/g;
    json = json.replace(reg, '$1\r\n');

    // remove multiple newlines
    reg = /(\r\n\r\n)/g;
    json = json.replace(reg, '\r\n');

    // remove newlines before commas
    reg = /\r\n\,/g;
    json = json.replace(reg, ',');

    // optional formatting...
    if (!options.newlineAfterColonIfBeforeBraceOrBracket) {
        reg = /\:\r\n\{/g;
        json = json.replace(reg, ':{');
        reg = /\:\r\n\[/g;
        json = json.replace(reg, ':[');
    }
    if (options.spaceAfterColon) {
        reg = /\:/g;
        json = json.replace(reg, ':');
    }

    jQuery.each(json.split('\r\n'), function(index, node) {
        var i = 0,
            indent = 0,
            padding = '';

        if (node.match(/\{$/) || node.match(/\[$/)) {
            indent = 1;
        } else if (node.match(/\}/) || node.match(/\]/)) {
            if (pad !== 0) {
                pad -= 1;
            }
        } else {
            indent = 0;
        }

        for (i = 0; i < pad; i++) {
            padding += PADDING;
        }

        formatted += padding + node + '\r\n';
        pad += indent;
    });

    return formatted.replace(/(^\s*)|(\s*$)/g, "");
};

var initUniform = function (els) {
    if (els) {
        jQuery(els).each(function () {
                if ($(this).parents(".checker").size() == 0) {
                    $(this).show();
                    $(this).uniform();
                }
            });
    } else {
        handleUniform();
    }
}
var blockUI = function (el) {
    if (jQuery('#loadingToast').css('display') != 'none') return;
    jQuery('#toastMsgLoading').html('正在提交');
    jQuery('#loadingToast').fadeIn(100);
}
var unblockUI = function (el) {
    if (jQuery('#loadingToast').css('display') == 'none') return;
    jQuery('#loadingToast').fadeOut(100);
}

var handleUniform = function () {
    if (!jQuery().uniform) {
        return;
    }
    var test = $("input[type=checkbox]:not(.toggle), input[type=radio]:not(.toggle, .star)");
    if (test.size() > 0) {
        test.each(function () {
            if ($(this).parents(".checker").size() == 0) {
                $(this).show();
                $(this).uniform();
            }
        });
    }
}

function ajaxErrorHandle(XMLHttpRequest, textStatus, errorThrown) {
    if (XMLHttpRequest.status==500){
        alert(XMLHttpRequest.status + " : " + errorThrown);
    } else if (XMLHttpRequest.responseText) {
        alert(XMLHttpRequest.responseText);
    } else if (textStatus) {
        alert(textStatus);
    }
}

var showToastMessage = function(msgtxt,callback) {
    if (jQuery('#toast').css('display') != 'none') return;
    jQuery('#toastMessage').html(msgtxt);
    jQuery('#toastError').css('display','block');
    jQuery('#toastSuccess').css('display','none');
    jQuery('#toast').fadeIn(100);
    setTimeout(function () {
        jQuery('#toast').fadeOut(50,callback);
    }, 1000);
}
var showToastSuccess = function(msgtxt,callback) {
    if (jQuery('#toast').css('display') != 'none') return;
    jQuery('#toastMessage').html(msgtxt);
    jQuery('#toastError').css('display','none');
    jQuery('#toastSuccess').css('display','block');
    jQuery('#toast').fadeIn(100);
    setTimeout(function () {
        jQuery('#toast').fadeOut(50,callback);
    }, 1000);
}
var showDialogMessage = function(msgtxt,callback) {
    jQuery('#dialogMessage').html(msgtxt);
    jQuery('#iosDialog2').fadeIn(200);
    jQuery('#iosDialog2 .weui-dialog__btn')[0].onclick = function(){
        jQuery(this).parents('.js_dialog').fadeOut(200,callback);
    };
    // jQuery('#iosDialog2').on('click', '.weui-dialog__btn', function(){
    //     jQuery(this).parents('.js_dialog').fadeOut(200,callback);
    // });
}
var showConfirmMessage = function(title,msgtxt,callback) {
    jQuery('#confirmTitle').html(title);
    jQuery('#confirmMessage').html(msgtxt);
    jQuery('#iosDialog1').fadeIn(200);
    jQuery('#iosDialog1 .weui-dialog__btn_primary')[0].onclick = function(){
        jQuery(this).parents('.js_dialog').fadeOut(200,callback);
    }
    // 用jQuery的bind或on每绑定一次，就为onclick事件添加了所执行代码，对话框弹出多次就会执行多次绑定的匿名函数，也会执行多次callback
    // jQuery('#iosDialog1 .weui-dialog__btn_primary').bind('click', function(){
    //     alert('inner')
    //     jQuery(this).parents('.js_dialog').fadeOut(200,callback);
    // });
    jQuery('#iosDialog1').on('click', '.weui-dialog__btn_default', function(){
        jQuery(this).parents('.js_dialog').fadeOut(200);
    });
}

var reloadAllItems = function(container,all_items,canmodi){
    jQuery(container).html('');
    jQuery.each(all_items, function(askidx, item) {
        var options = '';
        if (item.QI_TYPE!='T') {
            jQuery.each(item.QI_OPTION, function(opidx,opval) {
                if (item.QI_TYPE=='R' || item.QI_TYPE=='RA') {
                    if (item.QI_TYPE=='R') {
                        options += '<label class="radio"><input type="radio" id="ask'+askidx+'_op'+opidx+'" name="ask'+askidx+'" value="'+opidx+'" />'+opval+'</label>';
                    } else {
                        options += '<button class="btn" id="ask'+askidx+'_op'+(opidx+1)+'" name="ask'+askidx+'" onclick="clickRadio('+askidx+','+(opidx+1)+');">'+opval+'</button>&nbsp;';
                    }
                } else if (item.QI_TYPE=='C' || item.QI_TYPE=='CH') {
                    if (item.QI_TYPE=='C') {
                        options += '<label class="checkbox"><input type="checkbox" id="ask'+askidx+'_op'+opidx+'" name="ask'+askidx+'" value="'+opidx+'" />'+opval+'</label>';
                    } else {
                        options += '<button class="btn" id="ask'+askidx+'_op'+(opidx+1)+'" name="ask'+askidx+'" onclick="clickCheck('+askidx+','+(opidx+1)+');">'+opval+'</button>&nbsp;';
                    }
                } else if (item.QI_TYPE=='S') {
                    options += '<button class="btn" id="ask'+askidx+'_op'+(opidx+1)+'" name="ask'+askidx+'" onclick="clickStar('+askidx+','+(opidx+1)+');">'+(opidx+1)+'</button>&nbsp;';
                } else if (item.QI_TYPE=='B') {
                    var title = opidx==0?'是':(opidx==1?'否':'不确定');
                    options += '<button class="btn" id="ask'+askidx+'_op'+(opidx+1)+'" name="ask'+askidx+'" onclick="clickBoolean('+askidx+','+(opidx+1)+');">'+title+'</button>&nbsp;';
                } else {
                    options += '<label class="radio"><input type="radio" id="ask'+askidx+'_op'+opidx+'" name="ask'+askidx+'" value="'+opidx+'" />'+opval+'</label>';
                }
            });
        }
        var answerArea = '';
        if (item.QI_TYPE=='T') {
            options += '<div class="weui-cells" style="margin-top:0px"><div class="weui-cell"><div class="weui-cell__bd"><input type="text" autocomplete="off" class="weui-input" id="ask'+askidx+'" name="ask'+askidx+'" placeholder="请输入答案" onfocus="itemTGetFocus(this);" /></div></div></div>';
            answerArea = '<div class="accordion-inner" style="padding:0px">'+options+'</div>'
        } else {
            answerArea = '<div class="accordion-inner">'+options+'</div>'
        }
        var btns = '';
        if (canmodi) {
            var btns = '<div class="btn-group edit">\
                            <a class="btn" href="#" data-toggle="dropdown"><i class="icon-reorder"></i></a>\
                            <ul class="dropdown-menu" style="left:-122px;">\
                                <li><a href="javascript:clickEditAsk('+askidx+');"><i class="icon-pencil"></i> 编辑</a></li>\
                                <li><a href="javascript:clickDelAsk('+askidx+');"><i class="icon-trash"></i> 删除</a></li>\
                                <li><a href="javascript:clickMoveAsk('+askidx+');"><i class="icon-retweet"></i> 移动</a></li>\
                            </ul>\
                        </div>';
        };
        console.log(canmodi)
        jQuery(container).append('\
            <div class="accordion-group">\
                <div class="accordion-heading">\
                    <a class="accordion-toggle collapsed" data-toggle="collapse" data-parent="#accordion1" href="#collapse_'+askidx+'" id="a_ask_'+askidx+'" style="padding-right:'+(canmodi?'40':'15')+'px;">\
                    <i class="icon-question-sign"></i> '+(askidx+1)+'.'+item.QI_TITLE+(item.QI_TYPE=='CH'?'(多选)':(item.QI_TYPE=='RA'?'(单选)':''))+'\
                    </a>'+btns+'\
                </div>\
                <div id="collapse_'+askidx+'" class="accordion-body collapse in">'+answerArea+'</div>\
            </div>');
        if (item.QI_TYPE=='T') {
            jQuery('#collapse_'+askidx).on('shown.bs.collapse', function () {
                if (document.activeElement.id!='ask'+askidx) {
                    jQuery('#ask'+askidx).focus();
                };
            })
        }
    });
    initUniform();
    // jQuery('#collapse_0').collapse('show');
}

var itemTGetFocus = function(el) {
    var p = jQuery(el).parent().parent().parent().parent().parent();
    if (p.attr('class')=='accordion-body collapse') {
        // p.collapse('show');
    };
}
