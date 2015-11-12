# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

from scrapy.conf import settings
from scrapy.exceptions import DropItem
from twisted.enterprise import adbapi
from scrapy.pipelines.images import ImagesPipeline
from scrapy import Request
from scrapy.exporters import JsonLinesItemExporter
from scrapy.exporters import JsonItemExporter
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
import json

class DoubanmeinvPipeline(object):
    #插入的sql语句
    feed_key = ['feedId','userId','createOn','title','thumbUrl','href','description','pics']
    user_key = ['userId','name','avatar','homePage']
    user_feed_key = ['userId','feedId','title','thumbPic']
    insertFeed_sql = '''insert into MeiziFeed (%s) values (%s)'''
    insertUser_sql = '''insert into MeiziUser (%s) values (%s)'''
    insertUserFeed_sql = '''insert into MeiziUserFeed (%s) values (%s)'''
    feed_query_sql = "select * from MeiziFeed where feedId = %s"
    user_query_sql = "select * from MeiziUser where userId = %s"
    feed_seen_sql = "select feedId from MeiziFeed"
    user_seen_sql = "select userId from MeiziUser"

    def __init__(self):
        dbargs = settings.get('DB_CONNECT')
        db_server = settings.get('DB_SERVER')
        dbpool = adbapi.ConnectionPool(db_server,**dbargs)
        self.dbpool = dbpool
        #更新看过的id列表
        d = self.dbpool.runInteraction(self.update_feed_seen_ids)
        d.addErrback(self._database_error)
        u = self.dbpool.runInteraction(self.update_user_seen_ids)
        u.addErrback(self._database_error)

    def __del__(self):
        self.dbpool.close()

    #更新feed已录入的id列表
    def update_feed_seen_ids(self, tx):
        tx.execute(self.feed_seen_sql)
        result = tx.fetchall()
        if result:
            #id[0]是因为result的子项是tuple类型
            self.feed_ids_seen = set([id[0] for id in result])
        else:
            #设置已查看过的id列表
            self.feed_ids_seen = set()

    #更新user已录入的id列表
    def update_user_seen_ids(self, tx):
        tx.execute(self.user_seen_sql)
        result = tx.fetchall()
        if result:
            #id[0]是因为result的子项是tuple类型
            self.user_ids_seen = set([id[0] for id in result])
        else:
            #设置已查看过的id列表
            self.user_ids_seen = set()

    #处理每个item并返回
    def process_item(self, item, spider):
        query = self.dbpool.runInteraction(self._conditional_insert, item)
        query.addErrback(self._database_error, item)

        if(item['feedId'] in self.feed_ids_seen):
            raise DropItem("重复的数据:%s" % item['feedId'])
        else:
            print "新增Feed数据:%s" % item['feedId']
            return item

    #插入数据
    def _conditional_insert(self, tx, item):
        #插入Feed
        tx.execute(self.feed_query_sql, (item['feedId']))
        result = tx.fetchone()
        if result == None:
            print "将Feed数据存入数据库中:%s" % item['feedId']
            self.insert_data(item,self.insertFeed_sql,self.feed_key)
        # else:
        #     print "该feed已存在数据库中:%s" % item['feedId']
        #添加进seen列表中
        if item['feedId'] not in self.feed_ids_seen:
            # print "新增到feed_seen列表中的id是:%s" % item['feedId']
            self.feed_ids_seen.add(item['feedId'])
        # else:
            # print "该feed的id已存在:%s" % item['feedId']
        #插入User
        user = item['userInfo']
        tx.execute(self.user_query_sql, (user['userId']))
        user_result = tx.fetchone()
        if user_result == None:
            print "将User数据存入数据库中:%s" % user['userId']
            self.insert_data(user,self.insertUser_sql,self.user_key)
            for feed in user['feeds']:
                self.insert_data(feed,self.insertUserFeed_sql,self.user_feed_key)
        # else:
            # print "该用户已存在数据库:%s" % user['userId']
        #添加进seen列表中
        if user['userId'] not in self.user_ids_seen:
            # print "新增到user_seen列表中的id是:%s" % user['userId']
            self.user_ids_seen.add(user['userId'])
        # else:
            # print "该user的id已存在:%s" % user['userId']

    #插入数据到数据库中
    def insert_data(self, item, insert, sql_key):
        fields = u','.join(sql_key)
        qm = u','.join([u'%s'] * len(sql_key))
        sql = insert % (fields,qm)
        data = [item[k] for k in sql_key]
        return self.dbpool.runOperation(sql,data)

    #数据库错误
    def _database_error(self, e, item):
        print "Database error: ", e

class ImageCachePipeline(ImagesPipeline):
    def get_media_requests(self, item, info):
        pics = item['pics']
        list = json.loads(pics)
        for image_url in list:
            yield Request(image_url)

    def item_completed(self, results, item, info):
        image_paths=[x['path'] for ok,x in results if ok]
        # print "results是：%s \n" % results
        if not image_paths:
            print "图片未下载好:%s" % image_paths
            raise DropItem('图片未下载好 %s'%image_paths)

class JsonExportPipeline(JsonLinesItemExporter):
    def __init__(self):
        dispatcher.connect(self.spider_opened, signals.spider_opened)
        dispatcher.connect(self.spider_closed, signals.spider_closed)
        self.files = {}

    def spider_opened(self, spider):
        file = open('items.json', 'w+b')
        self.files[spider] = file
        self.exporter = JsonItemExporter(file)
        self.exporter.start_exporting()

    def spider_closed(self, spider):
        self.exporter.finish_exporting()
        file = self.files.pop(spider)
        file.write("]")
        file.close()

    def process_item(self, item, spider):
        self.exporter.export_item(item)
        return item

