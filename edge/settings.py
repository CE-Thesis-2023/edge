from typing import Dict

import yaml
from cerberus import Validator

DEFAULT_CAMERA_GLOBAL_ARGUMENTS = ["-hide_banner",
                                   "-loglevel", "warning", "-threads", "2"]

DEFAULT_CAMERA_OUTPUT_ARGUMENTS = ["-threads",
                                   "2",
                                   "-f",
                                   "rawvideo",
                                   "-pix_fmt",
                                   "yuv420p"]

schema = {
    'cameras': {
        'type': 'dict',
        'keysrules': {
            'type': 'string',
        },
        'valuesrules': {
            'type': 'dict',
            'schema': {
                'best_image_timeout': {
                    'type': 'integer',
                },
                'source': {
                    'type': 'dict',
                    'schema': {
                        'path': {
                            'type': 'string',
                            'required': True,
                        },
                        'global-args': {
                            'type': 'string',
                        },
                        'input-args': {
                            'type': 'string',
                            'required': True,
                        },
                        'output-args': {
                            'type': 'string',
                        },
                        'hardware-acceleration': {
                            'type': 'string',
                            'required': True,
                        },
                    },
                },
                'detect': {
                    'type': 'dict',
                    'schema': {
                        'height': {
                            'type': 'integer',
                        },
                        'width': {
                            'type': 'integer',
                        },
                        'fps': {
                            'type': 'integer',
                        },
                        'min_initialized': {
                            'type': 'integer',
                        },
                        'max_disappear': {
                            'type': 'integer',
                        },
                    },
                },
                'mqtt': {
                    'type': 'dict',
                    'schema': {
                        'host': {
                            'type': 'string',
                        },
                        'port': {
                            'type': 'integer',
                        },
                        'topic': {
                            'type': 'string',
                        },
                    },
                },
            }
        }
    }
}


def validate(data) -> Dict:
    v = Validator(schema)
    if not v.validate(data):
        return v.errors
    return {}


def load(path) -> Dict:
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    return data


def with_defaults(settings: Dict):
    cameras = settings['cameras']
    for _, values in cameras.items():
        if values.get('best_image_timeout') is None:
            values['best_image_timeout'] = 10
        if values.get('detect') is None:
            values['detect'] = {}
        detect = values['detect']
        if detect.get('height') is None:
            detect['height'] = 320
        if detect.get('width') is None:
            detect['width'] = 320
        if detect.get('fps') is None:
            detect['fps'] = 10
        if detect.get('min_initialized') is None:
            detect['min_initialized'] = 10
        if detect.get('max_disappear') is None:
            detect['max_disappear'] = 10
        if values.get('source') is None:
            values['source'] = {}
        source = values['source']
        if source.get('global-args') is None:
            source['global-args'] = " ".join(DEFAULT_CAMERA_GLOBAL_ARGUMENTS)
        if source.get('output-args') is None:
            source['output-args'] = " ".join(DEFAULT_CAMERA_OUTPUT_ARGUMENTS)
    return settings
