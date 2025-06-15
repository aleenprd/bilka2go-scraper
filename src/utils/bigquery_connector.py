from typing import Any, Dict, List, Union

from google.cloud import bigquery


class BigQueryConnector:
    def __init__(self, project_id) -> None:
        self.project_id = project_id
        self.client = bigquery.Client(project_id)

    def create_table(
        self,
        location: str,
        dataset_name: str,
        table_name: str,
        schema: List[bigquery.SchemaField],
    ) -> Union[None, bigquery.Table]:
        """Create a BigQuery table with the specified schema.

        Args:
            location (str): The desired location for the dataset.
            dataset_name (str): The name of the dataset.
            table_name (str): The name of the table.
            schema (List[bigquery.SchemaField[str, str]]): The schema definition for the table.

        Returns:
            Union[None, bigquery.Table]: The created table object, or None if there was an error.
        """
        # Create the dataset if it doesn't exist
        dataset_ref = self.client.dataset(dataset_name)  # project=self.project_id
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = location  # Set the desired location for the dataset

        try:
            self.client.create_dataset(dataset)
            print(f"Dataset {dataset_name} created successfully.")
        except Exception as e:
            print(f"Error creating dataset {dataset_name}:", e)
            return None

        # Create the table
        table_ref = dataset_ref.table(table_name)
        table = bigquery.Table(table_ref, schema=schema)

        try:
            self.client.create_table(table)
            print(f"Table {table_name} created successfully.")
        except Exception as e:
            print(f"Error creating table {table_name}:", e)
            return None

        return table

    def insert_rows(self, dataset: str, table: str, rows: List[Dict[str, Any]]) -> None:
        """Insert rows into a BigQuery table.

        Args:
            dataset (str): BigQuery dataset.
            table (str): The BigQuery table to insert the rows into.
            rows (List[Dict[str, Any]]): The list of rows to be inserted, where each row is represented as a dictionary.

        Returns:
            None: This function does not return a value.

        Note:
            The rows parameter should be a list of dictionaries, where each dictionary represents a row to be inserted.
            The keys of the dictionaries should correspond to the column names in the table, and the values should be
            the corresponding values for each column.

        Example:
            table = client.get_table("project_id.dataset_name.table_name")
            rows = [
                {"column1": value1, "column2": value2},
                {"column1": value3, "column2": value4},
                ...
            ]
            insert_rows(table, rows)
        """
        table_ref = self.client.dataset(dataset).table(table)
        table = self.client.get_table(table_ref)
        self.client.insert_rows_json(table, rows)

    def query_table(
        self, query: str, job_config: Union[None, bigquery.QueryJobConfig] = None
    ) -> Union[List[bigquery.table.Row], None]:
        """
        Query a BigQuery table and retrieve the resulting rows.

        Args:
            query (str): The SQL query to execute.
            job_config (bigquery.QueryJobConfig): the configuration of the BigQuery statement.

        Returns:
            Union[List[bigquery.Row], None]: A list of rows returned by the query,
            or None if there was an error executing the query.
        """
        try:
            query_job = self.client.query(query, job_config=job_config)
            rows = query_job.result()
            return list(rows)
        except Exception as e:
            print("Error occurred while querying table:", e)
            return None