import arcpy


def compare_feature_classes(feature_class_1, feature_class_2):
    # Get count of features in the first feature class
    count_fc1 = int(arcpy.GetCount_management(feature_class_1)[0])

    # Get count of features in the second feature class
    count_fc2 = int(arcpy.GetCount_management(feature_class_2)[0])

    # Calculate the difference
    difference = count_fc2 - count_fc1

    # Determine the appropriate message
    if difference > 0:
        print(f"There are {difference} more features in the second feature class.")
    elif difference < 0:
        print(f"There are {-difference} fewer features in the second feature class.")
    else:
        print("Both feature classes have the same number of features.")
