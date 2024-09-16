# coding: utf-8
#
# The MIT License (MIT)
#
# Copyright (c) 2016-2021 yutiansut/QUANTAXIS
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import json
import pandas as pd
import toml
import json
import configparser
import datetime
import time
import tushare as ts
from typing import Optional
from QUANTAXIS.QAUtil import (
    QA_util_date_int2str,
    QA_util_date_stamp,
    QASETTING,
    QA_util_log_info,
    QA_util_to_json_from_pandas,
)


def get_token(path: Optional[str] = None, format: str = "ini") -> str:
    """
    explanation:
        获取 Tushare token

    params:
        path ->
            含义: tushare 配置存放文件, 默认从 `~/.quantaxis/setting/config.ini` 中读取配置
            类型: str
            参数支持:  ~/.quantaxis/setting/config.ini
        format ->
            含义: tushare 配置文件格式, 默认为 `ini` 格式
            类型: str
            参数支持: ['toml', 'ini', 'json']
    returns:
        str: 实际 token
    """
    token = None
    if path is None:
        # 从~/.quantaxis/setting/config.ini中读取配置
        token = QASETTING.get_config("TSPRO", "token", None)
    else:
        if format == "toml":
            with open(path, "r", encoding="utf8") as f:
                config = toml.load(f)
                try:
                    token = config.get("TSPRO").get("token", None)
                except:
                    raise ValueError(f"读取 {path} token 失败")
        elif format == "json":
            with open(path, "r", encoding="utf8") as f:
                config = json.load(f)
                try:
                    token = config.get("TSPRO").get("token", None)
                except:
                    raise ValueError(f"读取 {path} token 失败")
        elif format == "ini":
            parser = configparser.ConfigParser()
            parser.read(path)
            try:
                token = parser.get("TSPRO", "token")
            except:
                raise ValueError(f"读取 {path} token 失败")
    if token is None:
        raise ValueError("请设置tushare的token")
    return token


def get_pro():
    """
    explanation:
        设置 Tushare pro

    returns:
        实际 tushare pro 接口
    """
    pro = None
    try:
        pro = ts.pro_api(get_token())
    except Exception as e:
        if isinstance(e, NameError):
            print("请设置tushare pro的token凭证码")
        else:
            print("请升级tushare 至最新版本 pip install tushare -U")
            print(e)
    if pro is None:
        raise ValueError("配置 tushare pro 失败")
    return pro


def QA_fetch_get_stock_adj(code, end=""):
    """获取股票的复权因子

    Arguments:
        code {[type]} -- [description]

    Keyword Arguments:
        end {str} -- [description] (default: {''})

    Returns:
        [type] -- [description]
    """

    pro = get_pro()
    adj = pro.adj_factor(ts_code=code, trade_date=end)
    return adj


def QA_fetch_stock_basic():
    def fetch_stock_basic():
        stock_basic = None
        try:
            pro = get_pro()
            stock_basic = pro.stock_basic(
                exchange="",
                list_status="L",
                fields="ts_code," "symbol," "name," "area,industry,list_date",
            )
        except Exception as e:
            print(e)
            print("except when fetch stock basic")
            time.sleep(1)
            stock_basic = fetch_stock_basic()
        return stock_basic

    return fetch_stock_basic()


def cover_time(date):
    """
    字符串 '20180101'  转变成 float 类型时间 类似 time.time() 返回的类型
    :param date: 字符串str -- 格式必须是 20180101 ，长度8
    :return: 类型float
    """
    datestr = str(date)[0:8]
    date = time.mktime(time.strptime(datestr, "%Y%m%d"))
    return date


def _get_subscription_type(if_fq):
    if str(if_fq) in ["qfq", "01"]:
        if_fq = "qfq"
    elif str(if_fq) in ["hfq", "02"]:
        if_fq = "hfq"
    elif str(if_fq) in ["bfq", "00"]:
        if_fq = None
    else:
        QA_util_log_info("wrong with fq_factor! using qfq")
        if_fq = "qfq"
    return if_fq


def QA_fetch_get_stock_day(name, start="", end="", if_fq="qfq", type_="pd"):
    def fetch_data():
        data = None
        try:
            time.sleep(0.002)
            pro = get_pro()
            data = ts.pro_bar(
                api=pro,
                ts_code=str(name),
                asset="E",
                adj=_get_subscription_type(if_fq),
                start_date=start,
                end_date=end,
                freq="D",
                factors=["tor", "vr"],
            ).sort_index()
            print("fetch done: " + str(name))
        except Exception as e:
            print(e)
            print("except when fetch data of " + str(name))
            time.sleep(1)
            data = fetch_data()
        return data

    data = fetch_data()

    data["date_stamp"] = data["trade_date"].apply(lambda x: cover_time(x))
    data["code"] = data["ts_code"].apply(lambda x: str(x)[0:6])
    data["fqtype"] = if_fq
    if type_ in ["json"]:
        data_json = QA_util_to_json_from_pandas(data)
        return data_json
    elif type_ in ["pd", "pandas", "p"]:
        data["date"] = pd.to_datetime(data["trade_date"], utc=False, format="%Y%m%d")
        data = data.set_index("date", drop=False)
        data["date"] = data["date"].apply(lambda x: str(x)[0:10])
        return data


def QA_fetch_get_stock_realtime():
    data = ts.get_today_all()
    data_json = QA_util_to_json_from_pandas(data)
    return data_json


def QA_fetch_get_stock_info(name):
    data = ts.get_stock_basics()
    try:
        return data if name == "" else data.loc[name]
    except:
        return None


def QA_fetch_get_stock_tick(name, date):
    if len(name) != 6:
        name = str(name)[0:6]
    return ts.get_tick_data(name, date)


def QA_fetch_get_stock_list():
    df = QA_fetch_stock_basic()
    return list(df.ts_code)


def QA_fetch_get_stock_time_to_market():
    data = ts.get_stock_basics()
    return data[data["timeToMarket"] != 0]["timeToMarket"].apply(
        lambda x: QA_util_date_int2str(x)
    )


def QA_fetch_get_trade_date(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    exchange: str = "SSE",
):
    """
    explanation:
        Tushare 获取交易日历的接口封装

    params:
        start_date ->
            含义: 起始时间, 默认从 "1990-12-19" 开始
            类型: int, str, datetime
            参数支持: [19910906, '1992-03-02', datetime.date(2024, 9, 16)]
        end_date ->
            含义: 截止时间
            类型: int, str, datetime, 默认截止为当前日期
            参数支持: [19910906, '1992-03-02', datetime.date(2024, 9, 16)]
        exchange ->
            含义: 交易所, 默认为上交所 SSE
            类型: str
            参数支持: ['SSE', 'SZSE', 'SHFE', 'DCE', 'CFFEX', 'CZCE', 'INE']
    """
    if start_date is None:
        start_date = "19901219"
    if end_date is None:
        end_date = datetime.date.today().strftime("%Y%m%d")
    start = pd.Timestamp(str(start_date)).strftime("%Y%m%d")
    end = pd.Timestamp(str(end_date)).strftime("%Y%m%d")
    pro = get_pro()
    data = pro.trade_cal(exchange=exchange, start_date=start, end_date=end)
    data = data.loc[data["is_open"] == 1]
    data["date_stamp"] = (
        data["cal_date"].map(str).apply(lambda x: QA_util_date_stamp(x))
    )
    data = data.rename(columns={"cal_date": "trade_date"})
    message = QA_util_to_json_from_pandas(
        data[["exchange", "trade_date", "pretrade_date", "date_stamp"]]
    )
    return message


def QA_fetch_get_lhb(date):
    return ts.top_list(date)


def QA_fetch_get_stock_money():
    pass


def QA_fetch_get_stock_block():
    """Tushare的版块数据

    Returns:
        [type] -- [description]
    """
    import tushare as ts

    csindex500 = ts.get_zz500s()
    try:
        csindex500["blockname"] = "中证500"
        csindex500["source"] = "tushare"
        csindex500["type"] = "csindex"
        csindex500 = csindex500.drop(["date", "name", "weight"], axis=1)
        return csindex500.set_index("code", drop=False)
    except:
        return None


# test

# print(get_stock_day("000001",'2001-01-01','2010-01-01'))
# print(get_stock_tick("000001.SZ","2017-02-21"))
if __name__ == "__main__":
    df = QA_fetch_get_stock_list()
    print(df)
