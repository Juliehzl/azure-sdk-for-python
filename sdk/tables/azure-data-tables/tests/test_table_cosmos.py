# coding: utf-8

# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
import sys
import locale
import os
from time import sleep

from azure.data.tables import TableServiceClient
from datetime import (
    datetime,
    timedelta,
)

from azure.data.tables import (
    ResourceTypes,
    AccountSasPermissions,
    TableSasPermissions,
    CorsRule,
    RetentionPolicy,
    UpdateMode,
    AccessPolicy,
    TableAnalyticsLogging,
    Metrics
)
from azure.core.pipeline import Pipeline
from azure.core.pipeline.policies import (
    HeadersPolicy,
    ContentDecodePolicy,
)

from _shared.testcase import (
    TableTestCase,
    RERUNS_DELAY,
    SLEEP_DELAY
)
from _shared.cosmos_testcase import CachedCosmosAccountPreparer

from devtools_testutils import CachedResourceGroupPreparer
from azure.data.tables._authentication import SharedKeyCredentialPolicy
from azure.data.tables._table_shared_access_signature import generate_account_sas
from azure.core.pipeline.transport import RequestsTransport
from azure.core.exceptions import (
    HttpResponseError,
    ResourceNotFoundError,
    ResourceExistsError
)

from devtools_testutils import CachedResourceGroupPreparer

# ------------------------------------------------------------------------------
TEST_TABLE_PREFIX = 'pytablesync'
# ------------------------------------------------------------------------------

def _create_pipeline(account, credential, **kwargs):
    # type: (Any, **Any) -> Tuple[Configuration, Pipeline]
    credential_policy = SharedKeyCredentialPolicy(account_name=account.name, account_key=credential)
    transport = RequestsTransport(**kwargs)
    policies = [
        HeadersPolicy(),
        credential_policy,
        ContentDecodePolicy(response_encoding="utf-8")]
    return Pipeline(transport, policies=policies)


class StorageTableTest(TableTestCase):

    # --Helpers-----------------------------------------------------------------
    def _get_table_reference(self, prefix=TEST_TABLE_PREFIX):
        table_name = self.get_resource_name(prefix)
        return table_name

    def _create_table(self, ts, prefix=TEST_TABLE_PREFIX, table_list=None):
        table_name = self._get_table_reference(prefix)
        try:
            table = ts.create_table(table_name)
            if table_list is not None:
                table_list.append(table)
        except ResourceExistsError:
            table = ts.get_table_client(table_name)
        return table

    def _delete_table(self, ts, table):
        if table is None:
            return
        try:
            ts.delete_table(table.table_name)
        except ResourceNotFoundError:
            pass

    def _delete_all_tables(self, ts):
        tables = ts.list_tables()
        for table in tables:
            try:
                ts.delete_table(table.table_name)
            except ResourceNotFoundError:
                pass


    # --Test cases for tables --------------------------------------------------
    @pytest.mark.skip("Cosmos Tables does not yet support service properties")
    @CachedResourceGroupPreparer(name_prefix="tablestest")
    @CachedCosmosAccountPreparer(name_prefix="tablestest")
    def test_create_properties(self, resource_group, location, cosmos_account, cosmos_account_key):
        # # Arrange
        ts = TableServiceClient(self.account_url(cosmos_account, "cosmos"), cosmos_account_key)
        table_name = self._get_table_reference()
        # Act
        created = ts.create_table(table_name)

        # Assert
        assert created.table_name == table_name

        # properties = ts.get_service_properties()
        ts.set_service_properties(analytics_logging=TableAnalyticsLogging(write=True))

        p = ts.get_service_properties()

        ts.set_service_properties(minute_metrics= Metrics(enabled=True, include_apis=True,
                                 retention_policy=RetentionPolicy(enabled=True, days=5)))

        ps = ts.get_service_properties()
        ts.delete_table(table_name)

        if self.is_live:
            sleep(SLEEP_DELAY)

    @CachedResourceGroupPreparer(name_prefix="tablestest")
    @CachedCosmosAccountPreparer(name_prefix="tablestest")
    def test_create_table(self, resource_group, location, cosmos_account, cosmos_account_key):
        # # Arrange
        ts = TableServiceClient(self.account_url(cosmos_account, "cosmos"), cosmos_account_key)

        table_name = self._get_table_reference()

        # Act
        created = ts.create_table(table_name)

        # Assert
        assert created.table_name == table_name
        ts.delete_table(table_name)

        if self.is_live:
            sleep(SLEEP_DELAY)

    @CachedResourceGroupPreparer(name_prefix="tablestest")
    @CachedCosmosAccountPreparer(name_prefix="tablestest")
    def test_create_table_fail_on_exist(self, resource_group, location, cosmos_account, cosmos_account_key):
        # Arrange
        ts = TableServiceClient(self.account_url(cosmos_account, "cosmos"), cosmos_account_key)
        table_name = self._get_table_reference()

        # Act
        created = ts.create_table(table_name)
        with pytest.raises(ResourceExistsError):
            ts.create_table(table_name)

        # Assert
        assert created
        ts.delete_table(table_name)

        if self.is_live:
            sleep(SLEEP_DELAY)

    @CachedResourceGroupPreparer(name_prefix="tablestest")
    @CachedCosmosAccountPreparer(name_prefix="tablestest")
    def test_query_tables_per_page(self, resource_group, location, cosmos_account, cosmos_account_key):
        # Arrange
        ts = TableServiceClient(self.account_url(cosmos_account, "cosmos"), cosmos_account_key)

        table_name = "mytable"

        for i in range(5):
            ts.create_table(table_name + str(i))

        query_filter = "TableName eq 'mytable0' or TableName eq 'mytable1' or TableName eq 'mytable2'"
        table_count = 0
        page_count = 0
        for table_page in ts.query_tables(filter=query_filter, results_per_page=2).by_page():

            temp_count = 0
            for table in table_page:
                temp_count += 1
            assert temp_count <= 2
            page_count += 1
            table_count += temp_count

        assert page_count == 2
        assert table_count == 3

        self._delete_all_tables(ts)

        if self.is_live:
            sleep(SLEEP_DELAY)

    @CachedResourceGroupPreparer(name_prefix="tablestest")
    @CachedCosmosAccountPreparer(name_prefix="tablestest")
    def test_create_table_invalid_name(self, resource_group, location, cosmos_account, cosmos_account_key):
        # Arrange
        ts = TableServiceClient(self.account_url(cosmos_account, "cosmos"), cosmos_account_key)
        invalid_table_name = "my_table"

        with pytest.raises(ValueError) as excinfo:
            ts.create_table(table_name=invalid_table_name)

        assert "Table names must be alphanumeric, cannot begin with a number, and must be between 3-63 characters long.""" in str(
            excinfo)

        if self.is_live:
            sleep(SLEEP_DELAY)

    @CachedResourceGroupPreparer(name_prefix="tablestest")
    @CachedCosmosAccountPreparer(name_prefix="tablestest")
    def test_delete_table_invalid_name(self, resource_group, location, cosmos_account, cosmos_account_key):
        # Arrange
        ts = TableServiceClient(self.account_url(cosmos_account, "cosmos"), cosmos_account_key)
        invalid_table_name = "my_table"

        with pytest.raises(ValueError) as excinfo:
            ts.create_table(invalid_table_name)

        assert "Table names must be alphanumeric, cannot begin with a number, and must be between 3-63 characters long.""" in str(
            excinfo)

        if self.is_live:
            sleep(SLEEP_DELAY)

    @CachedResourceGroupPreparer(name_prefix="tablestest")
    @CachedCosmosAccountPreparer(name_prefix="tablestest")
    def test_query_tables(self, resource_group, location, cosmos_account, cosmos_account_key):
        # Arrange
        ts = TableServiceClient(self.account_url(cosmos_account, "cosmos"), cosmos_account_key)
        table = self._create_table(ts)

        # Act
        tables = list(ts.list_tables())

        # Assert
        assert tables is not None
        assert len(tables) >=  1
        assert tables[0] is not None
        ts.delete_table(table.table_name)

        if self.is_live:
            sleep(SLEEP_DELAY)

    @CachedResourceGroupPreparer(name_prefix="tablestest")
    @CachedCosmosAccountPreparer(name_prefix="tablestest")
    def test_query_tables_with_filter(self, resource_group, location, cosmos_account, cosmos_account_key):
        # Arrange
        ts = TableServiceClient(self.account_url(cosmos_account, "cosmos"), cosmos_account_key)
        table = self._create_table(ts)

        # Act
        name_filter = "TableName eq '{}'".format(table.table_name)
        tables = list(ts.query_tables(filter=name_filter))

        # Assert
        assert tables is not None
        assert len(tables) ==  1
        ts.delete_table(table.table_name)

        self._delete_all_tables(ts)

        if self.is_live:
            sleep(SLEEP_DELAY)

    @CachedResourceGroupPreparer(name_prefix="tablestest")
    @CachedCosmosAccountPreparer(name_prefix="tablestest")
    def test_query_tables_with_num_results(self, resource_group, location, cosmos_account, cosmos_account_key):
        # Arrange
        prefix = 'listtable'
        ts = TableServiceClient(self.account_url(cosmos_account, "cosmos"), cosmos_account_key)
        table_list = []
        for i in range(0, 4):
            self._create_table(ts, prefix + str(i), table_list)

        # Act
        small_page = []
        big_page = []
        for s in next(ts.list_tables(results_per_page=3).by_page()):
            small_page.append(s)
            assert s.table_name.startswith(prefix)
        for t in next(ts.list_tables().by_page()):
            big_page.append(t)
            assert t.table_name.startswith(prefix)

        # Assert
        assert len(small_page) ==  3
        assert len(big_page) >=  4

        self._delete_all_tables(ts)

        if self.is_live:
            sleep(SLEEP_DELAY)

    @CachedResourceGroupPreparer(name_prefix="tablestest")
    @CachedCosmosAccountPreparer(name_prefix="tablestest")
    def test_query_tables_with_marker(self, resource_group, location, cosmos_account, cosmos_account_key):
        # Arrange
        ts = TableServiceClient(self.account_url(cosmos_account, "cosmos"), cosmos_account_key)
        prefix = 'listtable'
        table_names = []
        for i in range(0, 4):
            self._create_table(ts, prefix + str(i), table_names)

        # table_names.sort()

        # Act
        generator1 = ts.list_tables(results_per_page=2).by_page()
        next(generator1)
        generator2 = ts.list_tables(results_per_page=2).by_page(
            continuation_token=generator1.continuation_token)
        next(generator2)

        tables1 = generator1._current_page
        tables2 = generator2._current_page

        # Assert
        assert len(tables1) ==  2
        assert len(tables2) ==  2
        assert tables1 != tables2

        self._delete_all_tables(ts)

        if self.is_live:
            sleep(SLEEP_DELAY)

    @CachedResourceGroupPreparer(name_prefix="tablestest")
    @CachedCosmosAccountPreparer(name_prefix="tablestest")
    def test_delete_table_with_existing_table(self, resource_group, location, cosmos_account, cosmos_account_key):
        # Arrange
        ts = TableServiceClient(self.account_url(cosmos_account, "cosmos"), cosmos_account_key)
        table = self._create_table(ts)

        # Act
        deleted = ts.delete_table(table_name=table.table_name)

        # Assert
        existing = list(ts.query_tables("TableName eq '{}'".format(table.table_name)))
        assert len(existing) ==  0

        if self.is_live:
            sleep(SLEEP_DELAY)

    @CachedResourceGroupPreparer(name_prefix="tablestest")
    @CachedCosmosAccountPreparer(name_prefix="tablestest")
    def test_delete_table_with_non_existing_table_fail_not_exist(self, resource_group, location, cosmos_account,
                                                                 cosmos_account_key):
        # Arrange
        ts = TableServiceClient(self.account_url(cosmos_account, "cosmos"), cosmos_account_key)
        table_name = self._get_table_reference()

        # Act
        with pytest.raises(HttpResponseError):
            ts.delete_table(table_name)

        if self.is_live:
            sleep(SLEEP_DELAY)

    @pytest.mark.skip("Cosmos does not support table access policy")
    @CachedResourceGroupPreparer(name_prefix="tablestest")
    @CachedCosmosAccountPreparer(name_prefix="tablestest")
    def test_unicode_create_table_unicode_name(self, resource_group, location, cosmos_account, cosmos_account_key):
        # Arrange
        url = self.account_url(cosmos_account, "cosmos")
        ts = TableServiceClient(url, cosmos_account_key)
        table_name = u'啊齄丂狛狜'

        # Act
        with pytest.raises(HttpResponseError):
            ts.create_table(table_name)

        if self.is_live:
            sleep(SLEEP_DELAY)

    @pytest.mark.skip("Cosmos does not support table access policy")
    @CachedResourceGroupPreparer(name_prefix="tablestest")
    @CachedCosmosAccountPreparer(name_prefix="tablestest")
    def test_get_table_acl(self, resource_group, location, cosmos_account, cosmos_account_key):
        # Arrange
        url = self.account_url(cosmos_account, "cosmos")
        ts = TableServiceClient(self.account_url(cosmos_account, "cosmos"), cosmos_account_key)
        table = self._create_table(ts)
        try:
            # Act
            acl = table.get_table_access_policy()

            # Assert
            assert acl is not None
            assert len(acl) ==  0
        finally:
            ts.delete_table(table.table_name)

        if self.is_live:
            sleep(SLEEP_DELAY)

    @pytest.mark.skip("Cosmos does not support table access policy")
    @CachedResourceGroupPreparer(name_prefix="tablestest")
    @CachedCosmosAccountPreparer(name_prefix="tablestest")
    def test_set_table_acl_with_empty_signed_identifiers(self, resource_group, location, cosmos_account,
                                                         cosmos_account_key):
        # Arrange
        url = self.account_url(cosmos_account, "cosmos")
        ts = TableServiceClient(url, cosmos_account_key)
        table = self._create_table(ts)
        try:
            # Act
            table.set_table_access_policy(signed_identifiers={})

            # Assert
            acl = table.get_table_access_policy()
            assert acl is not None
            assert len(acl) ==  0
        finally:
            ts.delete_table(table.table_name)

        if self.is_live:
            sleep(SLEEP_DELAY)

    @pytest.mark.skip("Cosmos does not support table access policy")
    @CachedResourceGroupPreparer(name_prefix="tablestest")
    @CachedCosmosAccountPreparer(name_prefix="tablestest")
    def test_set_table_acl_with_empty_signed_identifier(self, resource_group, location, cosmos_account,
                                                        cosmos_account_key):
        # Arrange
        url = self.account_url(cosmos_account, "cosmos")
        ts = TableServiceClient(url, cosmos_account_key)
        table = self._create_table(ts)
        try:
            # Act
            table.set_table_access_policy(signed_identifiers={'empty': None})
            # Assert
            acl = table.get_table_access_policy()
            assert acl is not None
            assert len(acl) ==  1
            assert acl['empty'] is not None
            assert acl['empty'].permission is None
            assert acl['empty'].expiry is None
            assert acl['empty'].start is None
        finally:
            ts.delete_table(table.table_name)

        if self.is_live:
            sleep(SLEEP_DELAY)

    @pytest.mark.skip("Cosmos does not support table access policy")
    @CachedResourceGroupPreparer(name_prefix="tablestest")
    @CachedCosmosAccountPreparer(name_prefix="tablestest")
    def test_set_table_acl_with_signed_identifiers(self, resource_group, location, cosmos_account,
                                                   cosmos_account_key):
        # Arrange
        url = self.account_url(cosmos_account, "cosmos")
        ts = TableServiceClient(url, cosmos_account_key)
        table = self._create_table(ts)
        client = ts.get_table_client(table_name=table.table_name)

        # Act
        identifiers = dict()
        identifiers['testid'] = AccessPolicy(start=datetime.utcnow() - timedelta(minutes=5),
                                             expiry=datetime.utcnow() + timedelta(hours=1),
                                             permission='r')
        try:
            client.set_table_access_policy(signed_identifiers=identifiers)
            # Assert
            acl = client.get_table_access_policy()
            assert acl is not None
            assert len(acl) ==  1
            assert 'testid' in acl
        finally:
            ts.delete_table(table.table_name)

        if self.is_live:
            sleep(SLEEP_DELAY)

    @pytest.mark.skip("Cosmos does not support table access policy")
    @CachedResourceGroupPreparer(name_prefix="tablestest")
    @CachedCosmosAccountPreparer(name_prefix="tablestest")
    def test_set_table_acl_too_many_ids(self, resource_group, location, cosmos_account, cosmos_account_key):
        # Arrange
        url = self.account_url(cosmos_account, "cosmos")
        ts = TableServiceClient(url, cosmos_account_key)
        table = self._create_table(ts)
        try:
            # Act
            identifiers = dict()
            for i in range(0, 6):
                identifiers['id{}'.format(i)] = None

            # Assert
            with pytest.raises(ValueError):
                table.set_table_access_policy(table_name=table.table_name, signed_identifiers=identifiers)
        finally:
            ts.delete_table(table.table_name)

        if self.is_live:
            sleep(SLEEP_DELAY)

    @pytest.mark.skip("Cosmos Tables does not yet support sas")
    @pytest.mark.live_test_only
    @CachedResourceGroupPreparer(name_prefix="tablestest")
    @CachedCosmosAccountPreparer(name_prefix="tablestest")
    def test_account_sas(self, resource_group, location, cosmos_account, cosmos_account_key):
        # SAS URL is calculated from storage key, so this test runs live only

        # Arrange
        url = self.account_url(cosmos_account, "cosmos")
        tsc = TableServiceClient(url, cosmos_account_key)
        table = self._create_table(tsc)
        try:
            entity = {
                'PartitionKey': 'test',
                'RowKey': 'test1',
                'text': 'hello',
            }
            table.upsert_entity(mode=UpdateMode.MERGE, entity=entity)

            entity['RowKey'] = 'test2'
            table.upsert_entity(mode=UpdateMode.MERGE, entity=entity)

            token = generate_account_sas(
                cosmos_account.name,
                cosmos_account_key,
                resource_types=ResourceTypes(object=True),
                permission=AccountSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(hours=1),
                start=datetime.utcnow() - timedelta(minutes=1),
            )

            # Act
            service = TableServiceClient(
                self.account_url(cosmos_account, "cosmos"),
                credential=token,
            )
            sas_table = service.get_table_client(table.table_name)
            entities = list(sas_table.list_entities())

            # Assert
            assert len(entities) ==  2
            assert entities[0].text ==  'hello'
            assert entities[1].text ==  'hello'
        finally:
            self._delete_table(table=table, ts=tsc)

    @pytest.mark.skip("Test fails on Linux and in Python2. Throws a locale.Error: unsupported locale setting")
    @CachedResourceGroupPreparer(name_prefix="tablestest")
    @CachedCosmosAccountPreparer(name_prefix="tablestest")
    def test_locale(self, resource_group, location, cosmos_account, cosmos_account_key):
        # Arrange
        ts = TableServiceClient(self.account_url(cosmos_account, "cosmos"), cosmos_account_key)
        table = (self._get_table_reference())
        init_locale = locale.getlocale()
        if os.name == "nt":
            culture = "Spanish_Spain"
        elif os.name == 'posix':
            culture = 'es_ES.UTF-8'
        else:
            culture = 'es_ES.utf8'

        locale.setlocale(locale.LC_ALL, culture)
        e = None

        # Act
        ts.create_table(table)

        resp = ts.list_tables()

        e = sys.exc_info()[0]

        # Assert
        assert e is None

        ts.delete_table(table)
        locale.setlocale(locale.LC_ALL, init_locale[0] or 'en_US')

        if self.is_live:
            sleep(SLEEP_DELAY)
