from dagster import asset

@asset
def hi():
    return "hello"