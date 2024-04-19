import arcpy


def compare_feature_classes(feature_class_1, feature_class_2):
    # Get count of features in the first feature class
    count_fc1 = arcpy.GetCount_management(feature_class_1)[0]

    # Get count of features in the second feature class
    count_fc2 = arcpy.GetCount_management(feature_class_2)[0]

    # Calculate the difference
    difference = int(count_fc1) - int(count_fc2)

    # Print the result
    if difference > 0:
        print(f"There are {difference} fewer features in the second feature class.")
    elif difference < 0:
        print(f"There are {-difference} fewer features in the first feature class.")
    else:
        print("Both feature classes have the same number of features.")
