from input_data import input_n100
from env_setup import environment_setup
import config
import logging
from custom_tools import custom_arcpy

environment_setup.main()


def stress_test_select_location_and_make_permanent_feature():
    custom_arcpy.select_attribute_and_make_permanent_feature(
        input_n100.AdminFlate, "NAVN = 'Oslo'", "selection_fc"
    )
    selection_fc = "selection_fc"

    custom_arcpy.select_location_and_make_permanent_feature(
        input_n100.BygningsPunkt,
        custom_arcpy.OverlapType.INTERSECT,
        selection_fc,
        "selected_bygningspunkt",
    )
    selcted_bygningspunkt = "selected_bygningspunkt"

    custom_arcpy.select_location_and_make_permanent_feature(
        input_n100.ArealdekkeFlate,
        custom_arcpy.OverlapType.INTERSECT,
        selection_fc,
        "selected_arealdekkeflate",
    )
    selcted_arealdekkeflate = "selected_arealdekkeflate"

    # Set up logging
    logging.basicConfig(
        filename=r"C:\Users\oftell\Documents\Automatisk Generalisering\log\test_log.txt",
        level=logging.INFO,
    )
    logging.info("Starting tests...")

    input_layer = selcted_bygningspunkt
    select_features = selcted_arealdekkeflate

    # Iterate through all overlap types
    for overlap_type in custom_arcpy.OverlapType:
        # Iterate through all selection types
        for selection_type in custom_arcpy.SelectionType:
            # For both inverted and non-inverted
            for inverted in [True, False]:
                # If overlap_type is WITHIN_A_DISTANCE, test with a search_distance
                if overlap_type == custom_arcpy.OverlapType.WITHIN_A_DISTANCE:
                    search_distances = "10 Meters"
                    for dist in search_distances:
                        try:
                            custom_arcpy.select_location_and_make_permanent_feature(
                                input_layer,
                                overlap_type,
                                select_features,
                                "output_name_here",
                                selection_type,
                                inverted,
                                dist,
                            )
                            logging.info(
                                f"Success for combination: {overlap_type} - {selection_type} - {'Inverted' if inverted else 'Not Inverted'} - {dist}"
                            )
                        except Exception as e:
                            logging.error(
                                f"Error for combination: {overlap_type} - {selection_type} - {'Inverted' if inverted else 'Not Inverted'} - {dist}. Error message: {str(e)}"
                            )

                # For other overlap_types
                else:
                    try:
                        custom_arcpy.select_location_and_make_permanent_feature(
                            input_layer,
                            overlap_type,
                            select_features,
                            "output_name_here",
                            selection_type,
                            inverted,
                        )
                        logging.info(
                            f"Success for combination: {overlap_type} - {selection_type} - {'Inverted' if inverted else 'Not Inverted'}"
                        )
                    except Exception as e:
                        logging.error(
                            f"Error for combination: {overlap_type} - {selection_type} - {'Inverted' if inverted else 'Not Inverted'}. Error message: {str(e)}"
                        )

    logging.info("Tests completed.")
