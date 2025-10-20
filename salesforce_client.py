"""
Salesforce Client Module
Handles authentication and CRUD operations for Claim__c object
"""

import os
import json
import subprocess
import requests
from typing import Dict, List, Optional

class SalesforceClient:
    def __init__(self):
        self.access_token = None
        self.instance_url = None
        self.api_version = 'v60.0'

    def authenticate(self) -> bool:
        """Authenticate to Salesforce using JWT via Node.js script"""
        try:
            # Set environment variables
            env = os.environ.copy()
            env['SFDC_USERNAME'] = os.getenv('SFDC_USERNAME')
            env['KEY_PASS'] = os.getenv('KEY_PASS')
            env['SFDC_CLIENT_ID'] = os.getenv('SFDC_CLIENT_ID')
            env['SFDC_LOGIN_URL'] = os.getenv('SFDC_LOGIN_URL', 'https://login.salesforce.com')

            # Run the Node.js authentication script
            result = subprocess.run(
                ['node', 'sfdcJwtAuth.js'],
                env=env,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                raise Exception(f"Authentication failed: {result.stderr}")

            # Get the access token and instance URL from environment
            # The script sets SF_ACCESS_TOKEN and SF_INSTANCE_URL
            self.access_token = env.get('SF_ACCESS_TOKEN')
            self.instance_url = env.get('SF_INSTANCE_URL')

            # If not in env, try to get from sf CLI
            if not self.access_token:
                org_info = subprocess.run(
                    ['sf', 'org', 'display', '--target-org', 'myJwtOrg', '--json'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if org_info.returncode == 0:
                    org_data = json.loads(org_info.stdout)
                    self.access_token = org_data['result']['accessToken']
                    self.instance_url = org_data['result']['instanceUrl']

            if not self.access_token or not self.instance_url:
                raise Exception("Could not retrieve access token or instance URL")

            return True

        except Exception as e:
            raise Exception(f"Salesforce authentication failed: {str(e)}")

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for Salesforce API requests"""
        if not self.access_token:
            raise Exception("Not authenticated. Call authenticate() first.")
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make HTTP request with automatic token refresh on 401"""
        headers = kwargs.pop('headers', self._get_headers())

        # Make the request
        response = requests.request(method, url, headers=headers, **kwargs)

        # If unauthorized, re-authenticate and retry once
        if response.status_code == 401:
            print("Access token expired, re-authenticating...")
            self.authenticate()
            headers = self._get_headers()
            response = requests.request(method, url, headers=headers, **kwargs)

        return response

    def get_claim_fields(self) -> List[Dict]:
        """Get all fields from Claim__c object"""
        url = f"{self.instance_url}/services/data/{self.api_version}/sobjects/Claim__c/describe"
        response = self._make_request('GET', url)
        response.raise_for_status()

        data = response.json()
        fields = []

        for field in data['fields']:
            fields.append({
                'name': field['name'],
                'label': field['label'],
                'type': field['type'],
                'length': field.get('length'),
                'updateable': field['updateable'],
                'createable': field['createable']
            })

        return fields

    def get_all_records(self, fields: Optional[List[str]] = None) -> List[Dict]:
        """Get all Claim__c records"""
        if fields is None:
            # Get all fields first
            all_fields = self.get_claim_fields()
            # Filter to queryable fields
            fields = ['Id'] + [f['name'] for f in all_fields if f['name'] not in ['Id'] and f['type'] != 'address'][:50]

        fields_str = ', '.join(fields)
        query = f"SELECT {fields_str} FROM Claim__c"

        url = f"{self.instance_url}/services/data/{self.api_version}/query"
        params = {'q': query}

        response = self._make_request('GET', url, params=params)
        response.raise_for_status()

        data = response.json()
        return data.get('records', [])

    def get_record(self, record_id: str) -> Dict:
        """Get a single Claim__c record by ID"""
        # Get all fields
        all_fields = self.get_claim_fields()
        fields = ['Id'] + [f['name'] for f in all_fields if f['name'] not in ['Id'] and f['type'] != 'address'][:50]
        fields_str = ', '.join(fields)

        query = f"SELECT {fields_str} FROM Claim__c WHERE Id = '{record_id}'"
        url = f"{self.instance_url}/services/data/{self.api_version}/query"
        params = {'q': query}

        response = self._make_request('GET', url, params=params)
        response.raise_for_status()

        data = response.json()
        records = data.get('records', [])

        if not records:
            raise Exception(f"Record not found: {record_id}")

        return records[0]

    def update_record(self, record_id: str, fields: Dict) -> bool:
        """Update a Claim__c record"""
        url = f"{self.instance_url}/services/data/{self.api_version}/sobjects/Claim__c/{record_id}"

        response = requests.patch(url, headers=self._get_headers(), json=fields)
        response.raise_for_status()

        return True

    def create_record(self, fields: Dict) -> str:
        """Create a new Claim__c record"""
        url = f"{self.instance_url}/services/data/{self.api_version}/sobjects/Claim__c"

        response = requests.post(url, headers=self._get_headers(), json=fields)
        response.raise_for_status()

        data = response.json()
        return data['id']

    def delete_record(self, record_id: str) -> bool:
        """Delete a Claim__c record"""
        url = f"{self.instance_url}/services/data/{self.api_version}/sobjects/Claim__c/{record_id}"

        response = requests.delete(url, headers=self._get_headers())
        response.raise_for_status()

        return True

    # CRM Analytics methods
    def get_crm_analytics_datasets(self) -> List[Dict]:
        """Get all CRM Analytics datasets"""
        url = f"{self.instance_url}/services/data/{self.api_version}/wave/datasets"

        response = self._make_request('GET', url)
        response.raise_for_status()

        data = response.json()
        datasets = []

        for dataset in data.get('datasets', []):
            datasets.append({
                'id': dataset['id'],
                'name': dataset['name'],
                'developerName': dataset.get('currentVersionId', dataset['id']),
                'label': dataset.get('label', dataset['name']),
                'rowCount': dataset.get('totalRows', 0),
                'lastModifiedDate': dataset.get('lastModifiedDate'),
                'createdBy': dataset.get('createdBy', {}).get('name'),
                'type': dataset.get('type', 'dataset')
            })

        return datasets

    def get_dataset_fields(self, dataset_id: str) -> List[Dict]:
        """Get fields from a CRM Analytics dataset"""
        try:
            # First get the dataset version
            url = f"{self.instance_url}/services/data/{self.api_version}/wave/datasets/{dataset_id}"

            print(f"Fetching dataset info from: {url}")
            response = self._make_request('GET', url)
            response.raise_for_status()

            data = response.json()
            print(f"Dataset response: {json.dumps(data, indent=2)}")

            version_id = data.get('currentVersionId')

            if not version_id:
                print(f"No currentVersionId found in dataset data. Available keys: {data.keys()}")
                raise Exception(f"Could not find version for dataset {dataset_id}")

            print(f"Found version_id: {version_id}")

            # Get the XMD (metadata) for the dataset
            xmd_url = f"{self.instance_url}/services/data/{self.api_version}/wave/datasets/{dataset_id}/versions/{version_id}/xmds/main"

            print(f"Fetching XMD from: {xmd_url}")
            xmd_response = self._make_request('GET', xmd_url)
            xmd_response.raise_for_status()

            xmd_data = xmd_response.json()
            fields = []

            # Extract fields from dimensions and measures
            for dimension in xmd_data.get('dimensions', []):
                fields.append({
                    'name': dimension['field'],
                    'label': dimension.get('label', dimension['field']),
                    'type': 'dimension',
                    'dataType': dimension.get('type', 'Text')
                })

            for measure in xmd_data.get('measures', []):
                fields.append({
                    'name': measure['field'],
                    'label': measure.get('label', measure['field']),
                    'type': 'measure',
                    'dataType': measure.get('type', 'Numeric')
                })

            print(f"Found {len(fields)} fields")
            return fields

        except Exception as e:
            print(f"Error in get_dataset_fields: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    def query_dataset(self, dataset_id: str, fields: List[str], limit: int = 100, filters: Optional[Dict] = None) -> List[Dict]:
        """Query CRM Analytics dataset using SAQL"""
        try:
            # First, get the dataset to retrieve the currentVersionId
            dataset_url = f"{self.instance_url}/services/data/{self.api_version}/wave/datasets/{dataset_id}"
            dataset_response = self._make_request('GET', dataset_url)
            dataset_response.raise_for_status()
            dataset_data = dataset_response.json()

            version_id = dataset_data.get('currentVersionId')
            if not version_id:
                raise Exception(f"Could not find currentVersionId for dataset {dataset_id}")

            print(f"Dataset ID: {dataset_id}, Version ID: {version_id}")
            print(f"Full dataset data: {dataset_data}")

            # Build SAQL query using dataset_id/version_id format
            saql = f'q = load "{dataset_id}/{version_id}";'

            if filters:
                # Add filters if provided
                filter_conditions = []
                for field, value in filters.items():
                    filter_conditions.append(f'"{field}" == "{value}"')
                if filter_conditions:
                    saql += f'\nq = filter q by {" && ".join(filter_conditions)};'

            # Add projection - if fields provided
            if fields:
                # Don't quote field names in foreach generate
                fields_str = ', '.join(fields)
                saql += f'\nq = foreach q generate {fields_str};'

            # Add limit
            saql += f'\nq = limit q {limit};'

            print(f"Executing SAQL query:\n{saql}")

            # Execute query
            url = f"{self.instance_url}/services/data/{self.api_version}/wave/query"

            response = self._make_request('POST', url, json={'query': saql})

            # Check for errors
            if not response.ok:
                error_detail = response.text
                print(f"Query error: {error_detail}")
                raise Exception(f"Query failed with status {response.status_code}: {error_detail}")

            data = response.json()

            print(f"Query response structure: {json.dumps(data, indent=2)}")

            # Extract results - CRM Analytics returns data in a specific structure
            results = []
            if 'results' in data and 'records' in data['results']:
                raw_records = data['results']['records']

                # Convert CRM Analytics record format to flat dictionary
                for record in raw_records:
                    flat_record = {}
                    for key, value in record.items():
                        # CRM Analytics wraps values in objects with type info
                        if isinstance(value, dict) and 'value' in value:
                            flat_record[key] = value['value']
                        else:
                            flat_record[key] = value
                    results.append(flat_record)

                print(f"Converted {len(results)} records to flat format")
            else:
                print(f"Unexpected response structure. Keys: {data.keys()}")

            return results

        except requests.exceptions.HTTPError as e:
            error_msg = f"CRM Analytics query failed: {str(e)}"
            if e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = f"CRM Analytics query failed: {error_data}"
                except:
                    error_msg = f"CRM Analytics query failed: {e.response.text}"
            raise Exception(error_msg)
        except Exception as e:
            raise Exception(f"Error querying dataset: {str(e)}")
