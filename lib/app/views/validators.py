
class BaseValidator():
    schemas = {}

    def __init__(self, data):
        self.data = data

    def validate(self, schema):
        valid = True
        msg = ''
        required_keys = []
        for k, v in self.schemas[schema].items():
            if v['required'] == True:
                required_keys.append(k)

        missing = set(required_keys) - set(self.data.keys())
        if len(missing) > 0:
            valid = False
            msg = '{} are required.'.format(','.join(missing))
            return (valid, msg)

        for key,value in self.data:
            valid,msg = self.validate_key(schema, key)
            if not valid:
                return (valid, msg)

            valid,msg = self.validate_value(schema, key, value)
            if not valid:
                return (valid, msg)

        return (valid, msg)

    def validate_key(self, schema, key):
        msg = ''
        valid = True
        if key not in self.schemas[schema]:
            msg = '{} is not recognised'.format(key)
            valid = False

        return (valid, msg)

    def validate_value(self, schema, key, value):
        accepted_types = self.schemas[schema][key]
        msg = ''
        valid = False
        for type_ in accepted_types:
            if isinstance(value, type_):
                return (valid, msg)

        msg = '{} is not a valid type for {}'.format(type(value), key)
        return (valid, msg)


class ProfileValidator(BaseValidator):

    def __init__(self):
        super().__init__()
        self.schemas = {}



