class IncorrectOrbitException(Exception):
    '''Exception class triggered when the specified orbit does not retrieve any data between the two passed dates
    '''
    def __init__(self, orbit):
        msg = f"Incorrect orbit '{orbit}': No bands found in collection, please visit https://sentinel.esa.int/web/sentinel/missions/sentinel-1/observation-scenario for more info."
        super(IncorrectOrbitException, self).__init__(msg)