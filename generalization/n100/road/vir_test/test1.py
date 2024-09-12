# har tester ViR
import arcpy

from input_data import input_n50, input_n100
from file_manager.n100.file_manager_roads import Road_N100
from env_setup import environment_setup
from custom_tools.general_tools import custom_arcpy
from input_data import input_elveg
from custom_tools.decorators import timing_decorator


def main():
    environment_setup.main()
    #    creating_road_buffer()
    #    select_europaveg()
    select_kjorbare()
    select_kjorbareutenrampe()
    select_ramper()
    select_vegtrase()
    oslo()
    n50sti()
    n50stioslo()
    adding_fields_to_sti()
    adding_fields_to_vegtrase()
    n50stioslosingle()
    thin2000_sti()
    elvegsti()
    # delete_unwanted_fields()
    veger1()


# velg alle kjørbare veger
def select_kjorbare():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_elveg.Veglenke,
        expression="TYPEVEG = 'enkelBilveg' OR TYPEVEG = 'kanalisertVeg' OR TYPEVEG = 'rampe' OR TYPEVEG = 'rundkjøring'",
        output_name=Road_N100.test1___kjorbare___n100_road.value,
        selection_type="NEW_SELECTION",
    )


def select_kjorbareutenrampe():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___kjorbare___n100_road.value,
        expression="TYPEVEG='enkelBilveg' OR TYPEVEG='kanalisertVeg' OR TYPEVEG='rundkjøring'",
        output_name=Road_N100.test1___kjorbareutenrampe___n100_road.value,
        selection_type="NEW SELECTION",
    )


def select_ramper():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___kjorbare___n100_road.value,
        expression="TYPEVEG='rampe'",
        output_name=Road_N100.test1___ramper___n100_road.value,
        selection_type="NEW SELECTION",
    )


def select_vegtrase():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=Road_N100.test1___kjorbareutenrampe___n100_road.value,
        expression="DETALJNIVA IS NULL",
        output_name=Road_N100.test1___vegtrase___n100_road.value,
        selection_type="NEW SELECTION",
    )


def oslo():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n50.AdminFlate,
        expression="NAVN='Oslo'",
        output_name=Road_N100.test1___oslo___n100_road.value,
        selection_type="NEW_SELECTION",
    )


def n50sti():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_layer=input_n50.VegSti,
        expression="OBJTYPE='Sti' OR OBJTYPE='GangSykkelveg' OR OBJTYPE='Traktorveg' OR OBJTYPE='Barmarksløype'",
        output_name=Road_N100.test1___n50sti___n100_road.value,
        selection_type="NEW SELECTION",
    )


def n50stioslo():
    arcpy.analysis.Clip(
        in_features=Road_N100.test1___n50sti___n100_road.value,
        clip_features=Road_N100.test1___oslo___n100_road.value,
        out_feature_class=Road_N100.test1___n50stioslo___n100_road.value,
    )


def adding_fields_to_sti():
    arcpy.management.AddFields(
        in_table=Road_N100.test1___n50stioslo___n100_road.value,
        field_description=[
            ["inv_sti", "SHORT"],
            ["hie_sti", "SHORT"],
            ["inv_1", "SHORT"],
            ["hie_1", "SHORT"],
            ["merge", "LONG"],
            ["character", "SHORT"],
            ["inv_2", "SHORT"],
            ["hie_2", "SHORT"],
        ],
    )
    # Reclass function with added return statement for unmatched cases
    assign_hie_sti_to_sti = """def Reclass(subtypekode):
        if subtypekode == 6:
            return 1
        elif subtypekode == 8:
            return 2
        elif subtypekode == 10:
            return 3
        elif subtypekode == 11:
            return 4
        elif subtypekode == 9:
            return 10
        elif subtypekode == 7:
            return 3
        else:
            return None  # Return None or 0 for unmatched cases
    """

    # Calculate field for hie_1
    arcpy.management.CalculateField(
        in_table=Road_N100.test1___n50stioslo___n100_road.value,
        field="hie_sti",
        expression="Reclass(!subtypekode!)",
        expression_type="PYTHON3",
        code_block=assign_hie_sti_to_sti,
    )

    assign_hie_1_to_sti = """def Reclass(subtypekode):
        if subtypekode == 6:
            return 4
        elif subtypekode == 8:
            return 4
        elif subtypekode == 10:
            return 4
        elif subtypekode == 11:
            return 10
        elif subtypekode == 9:
            return 10
        elif subtypekode == 7:
            return 4
        else:
            return None  # Return None or 0 for unmatched cases
    """

    # Calculate field for hie_1
    arcpy.management.CalculateField(
        in_table=Road_N100.test1___n50stioslo___n100_road.value,
        field="hie_1",
        expression="Reclass(!subtypekode!)",
        expression_type="PYTHON3",
        code_block=assign_hie_1_to_sti,
    )


def adding_fields_to_vegtrase():
    arcpy.management.AddFields(
        in_table=Road_N100.test1___vegtrase___n100_road.value,
        field_description=[
            ["inv_1", "SHORT"],
            ["hie_1", "SHORT"],
            ["merge", "LONG"],
            ["character", "SHORT"],
            ["inv_2", "SHORT"],
            ["hie_2", "SHORT"],
        ],
    )
    # Reclass function with added return statement for unmatched cases
    assign_hie_1_to_vegtrase = """def Reclass(VEGKATEGORI):
        if VEGKATEGORI == 'E':
            return 1
        elif VEGKATEGORI == 'R':
            return 1
        elif VEGKATEGORI == 'F':
            return 1
        elif VEGKATEGORI == 'K':
            return 2
        elif VEGKATEGORI == 'P':
            return 3
        elif VEGKATEGORI == 'S':
            return 10
        else:
            return None  # Return None or 0 for unmatched cases
    """

    # Calculate field for hie_1
    arcpy.management.CalculateField(
        in_table=Road_N100.test1___vegtrase___n100_road.value,
        field="hie_1",
        expression="Reclass(!VEGKATEGORI!)",
        expression_type="PYTHON3",
        code_block=assign_hie_1_to_vegtrase,
    )
    # Calculate field for merge
    arcpy.management.CalculateField(
        in_table=Road_N100.test1___vegtrase___n100_road.value,
        field="merge",
        expression="!VEGNUMMER!",
        expression_type="PYTHON3",
    )

    assign_character_to_vegtrase = """def Reclass(TYPEVEG):
        if TYPEVEG == 'rundkjøring':
            return 0
        elif TYPEVEG == 'rampe':
            return 2
        elif TYPEVEG == 'enkelBilveg':
            return 1
        elif TYPEVEG == 'kanalisertVeg':
            return 1
        else:
            return None  # Return None or 0 for unmatched cases
    """

    # Calculate field for character
    arcpy.management.CalculateField(
        in_table=Road_N100.test1___vegtrase___n100_road.value,
        field="character",
        expression="Reclass(!TYPEVEG!)",
        expression_type="PYTHON3",
        code_block=assign_character_to_vegtrase,
    )


def n50stioslosingle():
    arcpy.management.MultipartToSinglepart(
        in_features=Road_N100.test1___n50stioslo___n100_road.value,
        out_feature_class=Road_N100.test1___n50stioslosingle___n100_road.value,
    )


def thin2000_sti():
    arcpy.cartography.ThinRoadNetwork(
        in_features=Road_N100.test1___n50stioslosingle___n100_road.value,
        minimum_length="2000 METER",
        invisibility_field="inv_sti",
        hierarchy_field="hie_sti",
    )


def elvegsti():
    # List fields from both datasets
    vegtrase_fields = [
        f.name for f in arcpy.ListFields(Road_N100.test1___vegtrase___n100_road.value)
    ]
    n50_fields = [
        f.name for f in arcpy.ListFields(Road_N100.test1___n50stioslo___n100_road.value)
    ]

    print("vegtrase fields:", vegtrase_fields)
    print("n50stioslosingle fields:", n50_fields)


def veger1():
    # Define feature classes
    fc1 = Road_N100.test1___n50stioslo___n100_road.value
    fc2 = Road_N100.test1___vegtrase___n100_road.value

    # Check if feature classes exist
    if arcpy.Exists(fc1) and arcpy.Exists(fc2):
        print(f"{fc1} and {fc2} exist and are ready for merging.")
    else:
        raise Exception(f"One or both datasets do not exist: {fc1}, {fc2}")

    # Want to merge these two feature classes together. Have a field that has the
    # same content but the names are slightly different: n50stioslo has subtypekode
    # and vegtrase has VEGKATEGORI. Name the output SUBTYP_VEGKAT.

    # Create FieldMappings object to manage merge output fields
    fieldMappings = arcpy.FieldMappings()
    fieldMappings.addTable(Road_N100.test1___n50stioslo___n100_road.value)
    fieldMappings.addTable(Road_N100.test1___vegtrase___n100_road.value)

    # # First get the subtypekode fieldmap. Then add the VEGKATEGORI field from vegtrase
    # # as an input field. Then replace the fieldmap within the fieldmappings object.
    fieldmap = fieldMappings.getFieldMap(fieldMappings.findFieldMapIndex("vegkategori"))
    fieldmap.addInputField(Road_N100.test1___vegtrase___n100_road.value, "VEGKATEGORI")
    fieldMappings.replaceFieldMap(
        fieldMappings.findFieldMapIndex("vegkategori"), fieldmap
    )

    # Remove the TRACTCODE fieldmap.
    # fieldMappings.removeFieldMap(fieldmappings.findFieldMapIndex("VEGKATEGORI"))

    # #Run Merge
    arcpy.management.Merge(
        inputs=[
            "Road_N100.test1___n50stioslo___n100_road.value",
            "Road_N100.test1___vegtrase___n100_road.value",
        ],
        output="Road_N100.test1___veger1___n100_road.value",
        field_mappings="fieldMappings",
    )


# def elvegsti():
#     # Create FieldMappings object to manage merging of fields
#     field_mappings = arcpy.FieldMappings()
#
#     # Add fields from the first dataset (vegtrase)
#     vegtrase_fields = arcpy.ListFields(Road_N100.test1___vegtrase___n100_road.value)
#     for field in vegtrase_fields:
#         field_map = arcpy.FieldMap()
#         field_map.addInputField(Road_N100.test1___vegtrase___n100_road.value, field.name)
#         field_mappings.addFieldMap(field_map)
#
#     # Add fields from the second dataset (n50stioslosingle)
#     n50_fields = arcpy.ListFields(Road_N100.test1___n50stioslosingle___n100_road.value)
#     for field in n50_fields:
#         field_map = arcpy.FieldMap()
#         field_map.addInputField(Road_N100.test1___n50stioslosingle___n100_road.value, field.name)
#
#         # If the field already exists in the field mappings, merge them
#         if field.name in [f.outputField.name for f in field_mappings.fields]:
#             for existing_field_map in field_mappings.fields:
#                 if existing_field_map.outputField.name == field.name:
#                     existing_field_map.addInputField(Road_N100.test1___n50stioslosingle___n100_road.value, field.name)
#         else:
#             # If the field doesn't exist, just add it
#             field_mappings.addFieldMap(field_map)
#
#     # Merge the datasets with field mapping
#     arcpy.management.Merge(
#         inputs=[
#             Road_N100.test1___vegtrase___n100_road.value,
#             Road_N100.test1___n50stioslosingle___n100_road.value,
#         ],
#         output=Road_N100.test1___elvegsti___n100_road.value,
#         field_mappings=field_mappings  # Pass the field mappings
#     )


if __name__ == "__main__":
    main()
