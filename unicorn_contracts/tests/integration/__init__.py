from pathlib import Path

from yaml import load
# From: https://pyyaml.org/wiki/PyYAMLDocumentation
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

import boto3


DEFAULT_SAM_CONFIG_FILE = Path(__file__).parent.parent.parent.resolve() / 'samconfig.yaml'
STACK_OUTPUTS = dict()

cfn = boto3.client("cloudformation")


def get_stack_name(samconfig: Path | str = DEFAULT_SAM_CONFIG_FILE) -> str:
    with open(samconfig, 'r') as f:
        conf = load(f, Loader=Loader)
        stack_name = conf['default']['global']['parameters']['stack_name']

    return stack_name


def get_stack_output(output_name: str, stack_name: str = get_stack_name()) -> str:
    """
    Get the value of an output 
    """

    if not (outputs := STACK_OUTPUTS.get(stack_name, dict())):
        try:
            response = cfn.describe_stacks(StackName=stack_name)
        except Exception as e:
            raise Exception(f"Cannot find stack {stack_name}. \n" f'Please make sure stack "{stack_name}" exists.') from e

        outputs = {o['OutputKey']: o['OutputValue'] for o in response["Stacks"][0]["Outputs"]}
        STACK_OUTPUTS[stack_name] = outputs

    try:
        return outputs[output_name]
    except KeyError as e:
        raise Exception(f"Unable to find Output {output_name} on stack {stack_name}") from e
