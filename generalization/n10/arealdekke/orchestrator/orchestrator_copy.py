import arcpy
from arealdekke_class import Arealdekke
from input_data import input_n10

def main():
    #Creates an instance of the arealdekke object.
    lyr="lyr"
    arcpy.management.MakeFeatureLayer(in_features=input_n10.Arealdekke_Buskerud, out_layer=lyr)
    arealdekke=Arealdekke(lyr)

    #Adds the categories to the arealdekke object
    yml_file=r"generalization\n10\arealdekke\orchestrator\arealdekke_categories_config.yml"
    arealdekke.add_categories(yml_file)

    #Process categories
    arealdekke.process_categories()

if __name__ == "__main__":
    main()