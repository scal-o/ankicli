import requestModule
"""Module to handle module-related requests"""


@requestModule.ensure_connectivity
def get_model_names():
    """Low-level function to gather all available models for the current user"""

    result = requestModule.request_action("modelNames")["result"]
    return result


@requestModule.ensure_connectivity
def get_model_fields(model_name):
    """Low -level function to gather available fields for a modelName"""

    result = requestModule.request_action("modelFieldNames", modelName=model_name)["result"]
    return result


def model_exists(model_name):
    """Low-level function to check if a certain modelName exists for the current user"""
    return model_name in model_list.keys()


def check_model_fields(model_name, model_fields):
    """Low-level function to check that all the fields provided are in the modelName definition"""

    actual_fields = model_list[model_name]
    actual_fields.sort()
    model_fields.sort()
    return model_fields == actual_fields


# define a dictionary containing all the models available for the current user
model_list = {}
if requestModule.check_connection():
    for name in get_model_names():
        model_list.setdefault(name, get_model_fields(name))
