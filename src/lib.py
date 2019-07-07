import configparser
from sqlalchemy import create_engine
import pandas as pd
# from openpyxl import load_workbook
import logging
import ast
from datetime import date, datetime
import calendar
from pandas import DataFrame
from typing import List, Union, Any
import re
from functools import partial
import numpy as np
import boto3
from InstagramAPI import InstagramAPI

artefacts_path = 'artefacts'
config = configparser.ConfigParser()
config.read('config.ini')

ig_username = config['instagram']['username']
ig_password = config['instagram']['password']

logger = logging.getLogger(__name__)


class DatabaseIO:
    list_cols = ['tags', 'dominant_color', 'posted_tags', 'last_color']
    bool_cols = ['accepted_static', 'accepted_ml', 'comments_disabled', 'is_private', 'is_verified', 'has_pf',
                 'is_business']
    date_cols ={
        'uploaded': ['uploaded_at', 'taken_at_datetime'],
        'users': ['followed_at', 'unfollowed_at'],
        'metadata': ['scraped_at'],
    }

    def __init__(self):
        db_config = config['db']
        url = db_config['url']
        db = db_config['schema']
        username = db_config['username']
        password = db_config['password']
        self.engine = create_engine(
            f"mysql+pymysql://{username}:{password}@{url}/{db}")

    def write_data(self, df, table):
        logger.info(f'Writing to {table}...')
        copy = df.copy()
        for col in copy.columns:
            if col in self.list_cols:
                copy[col] = copy[col].apply(str)
        copy.to_sql(table, self.engine, if_exists='replace', chunksize=1000, index=False)
        logger.info('Done.')

    def read_data(self, table, parse_dates=None):
        logger.info(f'Reading data from {table}...')
        if parse_dates is None: 
            parse_dates = []
        parse_dates = list(set(parse_dates + self.date_cols.get(table, [])))
        if parse_dates == []:
            parse_dates = False
        res = pd.read_sql_table(table, self.engine, parse_dates=parse_dates)

        for col in res.columns:
            if col in self.bool_cols:
                res[col] = res[col].astype('bool')
            if col in self.list_cols:
                res[col] = res[col].apply(ast.literal_eval)
        logger.info('Done.')
        return res


class CsvIO:
    @staticmethod
    def read_data(sheet, parse_dates=None, mode='csv'):
        if parse_dates is None: parse_dates = False
        if mode == 'csv': return pd.read_csv(f'{artefacts_path}/{sheet}.csv', sep=';', parse_dates=parse_dates,
                                             encoding='utf-8')
        if mode == 'excel': return pd.read_excel(f'{artefacts_path}/data.xlsx', sheet_name=sheet,
                                                 parse_dates=parse_dates)

    @staticmethod
    def write_data(df, sheet, mode='csv'):
        logger.info(f'Writing {sheet}...')
        assert isinstance(df, pd.DataFrame)
        if mode == 'csv': df.to_csv(f'{artefacts_path}/{sheet}.csv', sep=';', index=False)
        if mode == 'excel':
            filename = f'{artefacts_path}/data.xlsx'
            excel_book = load_workbook(filename)
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                writer.book = excel_book
                writer.sheets = dict((ws.title, ws) for ws in excel_book.worksheets)
                df.to_excel(writer, sheet_name=sheet, index=False)
                writer.save()
        logger.info(f'Done.')

        
def getApi():
    if 'api' not in globals():
        logger.info(f'No API connection found. Creating new connection...')
        global api
        api = InstagramAPI(ig_username, ig_password)
        api.login()
    else:
        logger.info(f'API connection found.')
    return api


def get_s3():
    session = boto3.Session(
        aws_access_key_id=config['aws']['AWSAccessKeyId'],
        aws_secret_access_key=config['aws']['AWSSecretKey'],
    )
    s3 = session.resource('s3', region_name='eu-west-1')
    return s3


def make_date(df: DataFrame, date_field: str):
    "Make sure `df[field_name]` is of the right date type."
    field_dtype = df[date_field].dtype
    if isinstance(field_dtype, pd.core.dtypes.dtypes.DatetimeTZDtype):
        field_dtype = np.datetime64
    if not np.issubdtype(field_dtype, np.datetime64):
        df[date_field] = pd.to_datetime(df[date_field], infer_datetime_format=True)


def cyclic_dt_feat_names(time: bool = True, add_linear: bool = False) -> List[str]:
    "Return feature names of date/time cycles as produced by `cyclic_dt_features`."
    fs = ['cos', 'sin']
    attr = [f'{r}_{f}' for r in 'weekday day_month month_year day_year'.split() for f in fs]
    if time: attr += [f'{r}_{f}' for r in 'hour clock min sec'.split() for f in fs]
    if add_linear: attr.append('year_lin')
    return attr


def cyclic_dt_features(d:Union[date,datetime], time: bool = True, add_linear: bool = False):
    "Calculate the cos and sin of date/time cycles."
    tt, fs = d.timetuple(), [np.cos, np.sin]
    day_year, days_month = tt.tm_yday, calendar.monthrange(d.year, d.month)[1]
    days_year = 366 if calendar.isleap(d.year) else 365
    rs = d.weekday() / 7, (d.day - 1) / days_month, (d.month - 1) / 12, (day_year - 1) / days_year
    feats = [f(r * 2 * np.pi) for r in rs for f in fs]
    if time and isinstance(d, datetime) and type(d) != date:
        rs = tt.tm_hour / 24, tt.tm_hour % 12 / 12, tt.tm_min / 60, tt.tm_sec / 60
        feats += [f(r * 2 * np.pi) for r in rs for f in fs]
    if add_linear:
        if type(d) == date:
            feats.append(d.year + rs[-1])
        else:
            secs_in_year = (datetime(d.year + 1, 1, 1) - datetime(d.year, 1, 1)).total_seconds()
            feats.append(d.year + ((d - datetime(d.year, 1, 1)).total_seconds() / secs_in_year))
    return feats


def add_cyclic_datepart(df: DataFrame, field_name: str, prefix: str = None, drop: bool = True, time: bool = False, add_linear: bool = False):
    "Helper function that adds trigonometric date/time features to a date in the column `field_name` of `df`."
    make_date(df, field_name)
    field = df[field_name]
    prefix = ifnone(prefix, re.sub('[Dd]ate$', '', field_name))
    series = field.apply(partial(cyclic_dt_features, time=time, add_linear=add_linear))
    columns = [prefix + c for c in cyclic_dt_feat_names(time, add_linear)]
    df_feats = pd.DataFrame([item for item in series], columns=columns)
    df = pd.concat([df, df_feats], axis=1)
    if drop: df.drop(field_name, axis=1, inplace=True)
    return df


def add_datepart(df: DataFrame, field_name: str, prefix: str = None, drop: bool = True, time: bool = False):
    "Helper function that adds columns relevant to a date in the column `field_name` of `df`."
    make_date(df, field_name)
    field = df[field_name]
    prefix = ifnone(prefix, re.sub('[Dd]ate$', '', field_name))
    attr = ['Year', 'Month', 'Week', 'Day', 'Dayofweek', 'Dayofyear', 'Is_month_end', 'Is_month_start',
            'Is_quarter_end', 'Is_quarter_start', 'Is_year_end', 'Is_year_start']
    if time: attr = attr + ['Hour', 'Minute', 'Second']
    for n in attr: df[prefix + n] = getattr(field.dt, n.lower())
    df[prefix + 'Elapsed'] = field.astype(np.int64) // 10 ** 9
    if drop: df.drop(field_name, axis=1, inplace=True)
    return df


def ifnone(a: Any, b: Any) -> Any:
    "`a` if `a` is not None, otherwise `b`."
    return b if a is None else a
