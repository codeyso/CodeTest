# -*- coding: utf-8 -*-
"""
-------------------------------------------------
   File Name：     check
   Description :   执行代理校验
   Author :        JHao
   date：          2019/8/6
-------------------------------------------------
   Change Activity:
                   2019/08/06: 执行代理校验
                   2021/05/25: 分别校验http和https
-------------------------------------------------
"""
__author__ = 'JHao'

from Proxy.util.six import Empty
from threading import Thread
from datetime import datetime
from Proxy.handler.logHandler import LogHandler
from Proxy.helper.validator import ProxyValidator
from Proxy.handler.configHandler import ConfigHandler
import threading

class DoValidator(object):
    """ 执行校验 """

    @classmethod
    def validator(cls, proxy):
        """
        校验入口
        Args:
            proxy: Proxy Object
        Returns:
            Proxy Object
        """
        http_r = cls.httpValidator(proxy)
        https_r = False if not http_r else cls.httpsValidator(proxy)

        proxy.check_count += 1
        proxy.last_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        proxy.last_status = True if http_r else False
        if http_r:
            if proxy.fail_count > 0:
                proxy.fail_count -= 1
            proxy.https = True if https_r else False
        else:
            proxy.fail_count += 1
        return proxy

    @classmethod
    def http_or_https(cls, proxy, anonymous=False):
        if anonymous:
            cls.anonymousValidator(proxy)
        else:
            if 'HTTPS' in proxy.https or '支持' in proxy.https:
                cls.httpsValidator(proxy)
            else:
                cls.httpValidator(proxy)
    @classmethod
    def httpValidator(cls, proxy):
        for func in ProxyValidator.http_validator:
            if not func(proxy):
                proxy.last_status = None
                return False
        proxy._https = 'HTTP'
        return True

    @classmethod
    def httpsValidator(cls, proxy):
        for func in ProxyValidator.https_validator:
            if not func(proxy):
                proxy.last_status = None
                return False
        proxy._https = 'HTTPS'
        return True

    @classmethod
    def preValidator(cls, proxy):
        for func in ProxyValidator.pre_validator:
            if not func(proxy):
                proxy.last_status = None
                return False
        return True

    @classmethod
    def anonymousValidator(cls, proxy):
        for func in ProxyValidator.anonymous_validator:
            if not func(proxy):
                proxy.last_status = None
                proxy._anonymous = '透明'
                return False
        proxy._anonymous = '高匿'
        return True


class _ThreadChecker(Thread):
    threadLock = threading.Lock()
    temp_list = []
    """ 多线程检测 """

    def __init__(self, work_type, target_queue, thread_name):
        Thread.__init__(self, name=thread_name)
        self.work_type = work_type
        self.log = LogHandler("checker")
        #self.proxy_handler = ProxyHandler()
        self.target_queue = target_queue
        self.conf = ConfigHandler()

    def run(self):
        self.log.info("{}ProxyCheck - {}: start".format(self.work_type.title(), self.name))
        while True:
            try:
                proxy = self.target_queue.get(block=False)
            except Empty:
                self.log.info("{}ProxyCheck - {}: complete".format(self.work_type.title(), self.name))
                break
            proxy = DoValidator.validator(proxy)

            if proxy.last_status or proxy.https:
                self.log.info('RawProxyCheck - {}: {} pass'.format(self.name, proxy.proxy.ljust(23)))
                _ThreadChecker.temp_list.append(proxy.proxy)
            else:
                self.log.info('RawProxyCheck - {}: {} fail'.format(self.name, proxy.proxy.ljust(23)))

            #if self.work_type == "raw":
            #    self.__ifRaw(proxy)
            #else:
            #    self.__ifUse(proxy)
            self.target_queue.task_done()

    #def __ifRaw(self, proxy):
    #    if proxy.last_status:
    #        if self.proxy_handler.exists(proxy):
    #            self.log.info('RawProxyCheck - {}: {} exist'.format(self.name, proxy.proxy.ljust(23)))
    #        else:
    #            self.log.info('RawProxyCheck - {}: {} pass'.format(self.name, proxy.proxy.ljust(23)))
    #            self.proxy_handler.put(proxy)
    #    else:
    #        self.log.info('RawProxyCheck - {}: {} fail'.format(self.name, proxy.proxy.ljust(23)))

    #def __ifUse(self, proxy):
    #    if proxy.last_status:
    #        self.log.info('UseProxyCheck - {}: {} pass'.format(self.name, proxy.proxy.ljust(23)))
    #        self.proxy_handler.put(proxy)
    #    else:
    #        if proxy.fail_count > self.conf.maxFailCount:
    #            self.log.info('UseProxyCheck - {}: {} fail, count {} delete'.format(self.name,
    #                                                                                proxy.proxy.ljust(23),
    #                                                                                proxy.fail_count))
    #            self.proxy_handler.delete(proxy)
    #        else:
    #            self.log.info('UseProxyCheck - {}: {} fail, count {} keep'.format(self.name,
    #                                                                              proxy.proxy.ljust(23),
    #                                                                              proxy.fail_count))
    #            self.proxy_handler.put(proxy)

def Checker(tp='raw', queue=None):
    """
    run Proxy ThreadChecker
    :param tp: raw/use
    :param queue: Proxy Queue
    :return:
    """
    thread_list = list()
    for index in range(20):
        thread_list.append(_ThreadChecker(tp, queue, "thread_%s" % str(index).zfill(2)))

    for thread in thread_list:
        thread.setDaemon(True)
        thread.start()

    for thread in thread_list:
        thread.join()

    return _ThreadChecker.temp_list