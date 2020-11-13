def populate_coordinates_dictionary(dictified_values, coordinates_dictionary):
    """
    The dictionnary coordinates_dictionary' will be populated (or updated) with
    values from the 'dictified_values' dictionnary

    Parameters
    ----------
    dictified_values :
        A dictionary of Sentinel-1 values

    coordinates_dictionary :
        A dictionnary matching to each coordinate key its values through time
        as well as its timestamps.

    Returns
    -------
    coordinates_dictionary
    """
    for entry in dictified_values:
        lat = entry["latitude"]
        lon = entry["longitude"]
        new_key = str(lat)+":"+str(lon)

        if new_key in coordinates_dictionary:
            # Retrieving measured value
            coordinates_dictionary[new_key]["VV"].append(entry["VV"])
            coordinates_dictionary[new_key]["VH"].append(entry["VH"])
            tmstp = entry["time"]
            coordinates_dictionary[new_key]["timestamps"].append(tmstp//1000)

        else:
            coordinates_dictionary[new_key] = {}
            # Retrieving measured value
            coordinates_dictionary[new_key]["lat"] = lat
            coordinates_dictionary[new_key]["lon"] = lon
            coordinates_dictionary[new_key]["VV"] = [entry["VV"]]
            coordinates_dictionary[new_key]["VH"] = [entry["VH"]]
            tmstp = entry["time"]
            coordinates_dictionary[new_key]["timestamps"] = [tmstp//1000]

    return coordinates_dictionary
