from id_validator import validator

ids = []

for id in ids:
    if(validator.is_valid(id)):
        print(id + ' is valid')
        print(validator.get_info(id))
