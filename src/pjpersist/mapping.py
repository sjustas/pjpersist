##############################################################################
#
# Copyright (c) 2011 Zope Foundation and Contributors.
# Copyright (c) 2014 Shoobx Inc.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""PostGreSQL/JSONB Mapping Implementations"""
from __future__ import absolute_import
import UserDict

from pjpersist import serialize

class PJTableMapping(UserDict.DictMixin, object):
    __pj_database__ = None
    __pj_table__ = None
    __pj_mapping_key__ = 'key'

    def __init__(self, jar):
        self._pj_jar = jar

    def __pj_filter__(self):
        return 'true'

    def __getitem__(self, key):
        filter = self.__pj_filter__()
        filter += ''' AND data @> '{"%s": "%s"}' ''' % (
            self.__pj_mapping_key__, key)
        with self._pj_jar.getCursor() as cur:
            cur.execute(
                'SELECT id FROM ' + self.__pj_table__ + ' WHERE ' + filter)
            if not cur.rowcount:
                raise KeyError(key)
            id = cur.fetchone()['id']
            dbref = serialize.DBRef(
                self.__pj_table__,
                id,
                self.__pj_database__ or self._pj_jar.database)
        return self._pj_jar.load(dbref)

    def __setitem__(self, key, value):
        # Even though setting the attribute should register the object with
        # the data manager, the value might not be in the DB at all at this
        # point, so registering it manually ensures that new objects get added.
        self._pj_jar.register(value)
        setattr(value, self.__pj_mapping_key__, key)

    def __delitem__(self, key):
        # Deleting the object from the database is not our job. We simply
        # remove it from the dictionary.
        value = self[key]
        filter += '''AND data @> '{"%s": %%s}' ''' % self.__pj_mapping_key__
        setattr(value, self.__pj_mapping_key__, None)

    def keys(self):
        filter = self.__pj_filter__()
        filter += " AND (data->>'%s') is not null" % self.__pj_mapping_key__
        with self._pj_jar.getCursor() as cur:
            cur.execute(
                'SELECT * FROM ' + self.__pj_table__ + ' WHERE ' + filter)
            return [
                res['data'][self.__pj_mapping_key__]
                for res in cur.fetchall()]