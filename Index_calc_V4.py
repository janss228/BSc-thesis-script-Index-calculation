# Author: Tim Willem Janssen
# Mail: timwjanssen@gmail.com

"""
INPUTS:
    Path to geodatabase containing all the following input data:
        Mask polygon
        RED, GREEN, REG, NIR rasters
        DEM raster
        Excel sheet
        SMC validation raster
    Path to geodatabase that will function as the temporary storage

OUTPUTS:
    Raster named 'Master' containing all calculated indices
"""


"""____________SCRIPT PREPARATION____________"""

# Import packages
import arcpy
import pandas as pd
import math


# Get user inputs
while True:
    answer_res_change = input("Change index resolutions? y/n")
    if answer_res_change == 'y':
        new_res_value_float = float(input("New resolution? (m)"))
        print("New resolution set to " + str(new_res_value_float) + "m")
        res_change_bool = True
        break
    elif answer_res_change == 'n':
        print('No resolution change confirmed')
        res_change_bool = False
        break
    else:
        print('Please answer with either "y" or "n"')

# Set working environments
arcpy.env.workspace = r"C:\Users\timwj\Documents\ArcGIS\Projects\AGP Thesis\Index workspace.gdb"
arcpy.env.scratchWorkspace = r"C:\Users\timwj\Documents\ArcGIS\Projects\AGP Thesis\Index scratch workspace.gdb"
arcpy.env.overwriteOutput = True

# Import the mask
mask = arcpy.FeatureClassToFeatureClass_conversion("Dry_cover", arcpy.env.scratchWorkspace, "mask")

# Import all rasters from the geodatabase and create a list of the multispectral data
RED = arcpy.Raster("MavigGRS_F2_V6_RED")
NIR = arcpy.Raster("MavigGRS_F2_V6_NIR")
GRE = arcpy.Raster("MavigGRS_F2_V6_GRE")
REG = arcpy.Raster("MavigGRS_F2_V6_REG")
DEM = arcpy.Raster("Culemborg_DTM_corrected")
SMC = arcpy.Raster("Krig_OK_raster_masked")
multispec_raster_list = [RED, NIR, GRE, REG]

# If resolution will not change, get the original resolution from the DEM raster metadata
if not res_change_bool:
    new_res_value_float = round(float(arcpy.GetRasterProperties_management(DEM, "CELLSIZEX").getOutput(0)
                                      .replace(',', '.')), 2)

# Save the SMC validation raster in the scratch workspace
SMC.save(arcpy.env.scratchWorkspace + "\\" + "SMC")

# Import the VI sheet
# df = pd.read_csv(r"C:\Users\timwj\Documents\ArcGIS\Projects\AGP Thesis\Index workspace.gdb\Index_sheet", delimiter=';')
# VI_list = arcpy.TableToTable_conversion("Index_sheet", arcpy.env.scratchWorkspace, "VI_list")
df = pd.read_csv(r"C:\Users\timwj\Documents\WUR\Thesis\Data\Python\Index_sheet.csv", delimiter=';')
VI_listoflists = [list(row) for row in df.values]

# Create a master list were all index strings will be added to
master_list = ["SMC"]


"""____________SET VI RESOLUTION____________"""


def fun_resample(in_raster, out_raster):
    """Resample the raster resolution to the new resolution defined earlier and save the new raster"""
    out_scratch_str = (arcpy.env.scratchWorkspace + "\\" + out_raster)
    arcpy.Resample_management(in_raster,
                              out_scratch_str,
                              cell_size=new_res_value_float,
                              resampling_type='BILINEAR')


def fun_resample_all():
    """Go through the original multispectral rasters, change the resolutions and save the new rasters"""
    multispec_raster_list_new_res = []
    for i in multispec_raster_list:
        new_res_name = (str(i) + '_res_' + str(new_res_value_float) + 'm')
        new_res_name = new_res_name.replace('.', '_')
        multispec_raster_list_new_res.append(new_res_name)
        print("The new resolution of " + str(i) + " is " + str(new_res_value_float) + " m")
        fun_resample(i, new_res_name)
        print(new_res_name + " has been saved")
    return multispec_raster_list_new_res
#change code giving rastes new name, can be more efficient


# If VI resolution is set to change, run resample functions and redefine the rasters
if res_change_bool:
    multispec_raster_list_new_res = fun_resample_all()
    RED = arcpy.Raster(arcpy.env.scratchWorkspace + "\\" + multispec_raster_list_new_res[0])
    NIR = arcpy.Raster(arcpy.env.scratchWorkspace + "\\" + multispec_raster_list_new_res[1])
    GRE = arcpy.Raster(arcpy.env.scratchWorkspace + "\\" + multispec_raster_list_new_res[2])
    REG = arcpy.Raster(arcpy.env.scratchWorkspace + "\\" + multispec_raster_list_new_res[3])


"""____________CALCULATE VI'S____________"""


def fun_VI_calc(formula_str, out_raster):
    """Calculate a vegetation index using the formula, mask with workingmask, and save as the out_raster input"""
    VI_raster = eval(formula_str)
    VI_raster = arcpy.sa.ExtractByMask(VI_raster, mask)
    VI_raster.save(arcpy.env.scratchWorkspace + "\\" + out_raster)


def fun_calc_all():
    """Iterate through the index matrix so all indices will be calculated using the fun_CI_calc function"""
    for i in VI_listoflists:
        fun_VI_calc(i[1], i[0])
        print('Index ' + i[0] + ' has been calculated')


# Run calc_all function so all indices will be calculated
fun_calc_all()

# Add all calculated indices to the master_index_list
master_list += [row[0] for row in VI_listoflists]

"""____________SET TI RESOLUTION____________"""


def fun_resample_DEM(in_raster, out_raster, mask_bool):
    """Mask and resample the DEM resolution to the new resolution defined earlier and save the new raster"""
    out_str = (arcpy.env.scratchWorkspace + "\\" + out_raster)
    if mask_bool:
        in_raster = arcpy.sa.ExtractByMask(in_raster, mask)
    arcpy.Resample_management(in_raster,
                              out_str,
                              cell_size=new_res_value_float,
                              resampling_type='BILINEAR')


# If TI resolution is set to change then mask, rename (to DTM), fill, resample, save, and import the DEM
# if res_change_bool:
DTM = arcpy.sa.Fill(DEM)
fun_resample_DEM(DTM, 'DTM', mask_bool=True)
fun_resample_DEM(DTM, 'DTM_working', mask_bool=False)
DTM_working = arcpy.Raster(arcpy.env.scratchWorkspace + "\\" + "DTM_working")

# If TI resolution is not set to change then fill and rename the DEM to DTM
# if not res_change_bool:
#     DTM = arcpy.sa.Fill(DEM)
#     DTM.save(arcpy.env.scratchWorkspace + "\\" + "DTM_working")
#     DTM_masked = arcpy.sa.ExtractByMask(DTM, mask)
#     DTM_masked.save(arcpy.env.scratchWorkspace + "\\" + "DTM")
#     DTM_working = arcpy.Raster(arcpy.env.scratchWorkspace + "\\" + "DTM_working")

# Add the calculated index string to the master list
master_list += ["DTM"]


"""__________CALCULATE SLOPE__________"""

# Run the Slope tool to create a slope raster and save the raster
slope_raster = arcpy.sa.Slope(DTM_working,
                              output_measurement='DEGREE')
slope_raster_masked = arcpy.sa.ExtractByMask(slope_raster, mask)
slope_out_str = "Slope"
slope_raster_masked.save(arcpy.env.scratchWorkspace + "\\" + slope_out_str)
master_list += [slope_out_str]
print(slope_out_str + ' has been created and saved')


"""__________CALCULATE CURVATURE__________"""

# Run the Curvature tool to create a slope raster and save the raster
curvature_raster = arcpy.sa.Curvature(DTM_working)
curvature_raster_masked = arcpy.sa.ExtractByMask(curvature_raster, mask)
curvature_out_str = "Curvature"
curvature_raster_masked.save(arcpy.env.scratchWorkspace + "\\" + curvature_out_str)
master_list += [curvature_out_str]
print(curvature_out_str + ' has been created and saved')


"""__________CALCULATE FLOW ACCUMULATION__________"""

# Run the FlowDirection tool to create a flow direction raster
flow_direction_raster = arcpy.sa.FlowDirection(DTM_working,
                                               force_flow='FORCE',
                                               flow_direction_type='DINF')

# Run the Flow Accumulation (FA) tool to create a FA raster and save the raster
flow_accumulation_raster = arcpy.sa.FlowAccumulation(flow_direction_raster,
                                                     flow_direction_type='DINF')
flow_accumulation_raster_masked = arcpy.sa.ExtractByMask(flow_accumulation_raster, mask)
FA_out_str = "FA"
# arcpy.Rename_management(arcpy.env.scratchWorkspace + "\\" + "Extract_Curv1",
#                         arcpy.env.scratchWorkspace + "\\" + FA_out_str)
flow_accumulation_raster_masked.save(arcpy.env.scratchWorkspace + "\\" + FA_out_str)
master_list += [FA_out_str]
print(FA_out_str + ' has been created and saved')


"""__________CALCULATE LS FACTOR__________"""

# Calculate the LS factor using the Slope and Flow Accumulation rasters created earlier
slope_raster_masked_product = slope_raster_masked * 0.01745
slope_raster_masked_sine = arcpy.sa.Sin(slope_raster_masked_product)
LS_raster = (flow_accumulation_raster_masked * new_res_value_float / 22.1) ** 0.4 * ((slope_raster_masked_sine / 0.09)
                                                                                     ** 1.4) * 1.4
LS_raster_masked = arcpy.sa.ExtractByMask(LS_raster, mask)
LS_out_str = "LS"
LS_raster_masked.save(arcpy.env.scratchWorkspace + "\\" + LS_out_str)
master_list += [LS_out_str]
print(LS_out_str + ' has been created and saved')


"""__________CALCULATE TWI__________"""

# Convert the slope raster values from degrees to radians
slope_raster_masked_radians = slope_raster_masked * math.pi / 180.0

# Create the TWI raster using the Ln tool and save it in the workspace
TWI_raster = arcpy.sa.Ln(flow_accumulation_raster_masked / (arcpy.sa.Tan(slope_raster_masked_radians) + 0.01))
TWI_raster_masked = arcpy.sa.ExtractByMask(TWI_raster, mask)
TWI_out_str = "TWI"
TWI_raster_masked.save(arcpy.env.scratchWorkspace + "\\" + TWI_out_str)
master_list += [TWI_out_str]
print(TWI_out_str + ' has been created and saved')


"""____________CREATE MASTER RASTER____________"""

# Create the name of the master file which includes the resolution of the rasters
master_name_str = 'Master_' + str(new_res_value_float).replace('.', '_') + 'm_dry_cover'

print(master_list)

# Add the scratch workspace string to the master list
master_list_scratch = []
for i in master_list:
    master_list_scratch += [arcpy.env.scratchWorkspace + "\\" + i]

# Combine all vegetation and topographic indices and the SMC validation dataset into 1 master raster file
arcpy.CompositeBands_management(master_list_scratch, master_name_str)


"""____________RENAME BANDS IN MASTER RASTER____________"""

n = 0
for name in master_list:
    n += 1
    arcpy.Rename_management(master_name_str + r"\Band_" + str(n), master_name_str + r"\\" + name)

print("All bands in the master raster have been renamed")
print("Closing script....")
