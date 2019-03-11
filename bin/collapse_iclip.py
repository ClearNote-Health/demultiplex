#!/usr/bin/env python

import re
import pandas as pd
import argparse
import csv

# need args for directory to put 10X samplesheet if applicable
argparser = argparse.ArgumentParser()
argparser.add_argument('--samplesheet', type=str)
ARGS = argparser.parse_args()

samplesheet = ARGS.samplesheet

# function to get idx of Data tag
data_tag_search = '[Data]'
data_index = 0
with open(samplesheet, 'r') as f:
    reader = csv.reader(f, delimiter=',')
    for idx, row in enumerate(reader):
        if data_tag_search in row:
            data_index = idx

iclip = 'iCLIP'

sample_pd = pd.read_csv(samplesheet, skiprows=range(0, data_index + 1))
sample_pd['index'] = sample_pd['index'].astype('str')
sample_pd['index2'] = sample_pd['index2'].astype('str')

# find iclip in data type col and collapse them into one each lane
iclip_select = sample_pd.loc[sample_pd['index'] == iclip].copy()
iclip_lanes_set = iclip_select['Lane'].unique().tolist()

idx_list_to_drop = []
for lane in iclip_lanes_set:
    # float infinity values are guaranteed to be larger or smaller than any other number
    min_value, max_value = float('inf'), float('-inf')
    sample_ID = ''
    iclip_sample_name = ''
    count = 0
    for index, row in iclip_select.iterrows():
        if lane == row['Lane']:
            # regex to find project limsid and number
            sample_num = re.search("(.*?)A([0-9]+$)", row['Sample_ID'])
            iclip_sample_num = sample_num.group(2)

            if int(iclip_sample_num) > max_value:
                max_value = int(iclip_sample_num)
            elif int(iclip_sample_num) < min_value:
                min_value = int(iclip_sample_num)

            if count == 0:
                # regex to find sample_name without number attached
                iclip_sample_name_search = re.search("(.* ?_). *", row['Sample_Name'])
                iclip_sample_name = iclip_sample_name_search.group(1)
                sample_ID = sample_num.group(1)
            # get list to drop rows by idx after first row
            elif count != 0:
                idx_list_to_drop.append(index)
            count = count + 1

    # create new ID's and names
    new_sample_ID = sample_ID + 'A' + str(min_value) + '-A' + str(max_value)
    new_sample_name = iclip_sample_name + "pool"
    # change the Sample_ID and Sample_Name of first row with matching lane (not in idx list)
    sample_pd.loc[(sample_pd['Lane'] == lane) & (~sample_pd.index.isin(idx_list_to_drop)),
                  ['Sample_ID', 'Sample_Name','index', 'index2']] = new_sample_ID, new_sample_name, '', ''

# remove rows and create new samplesheet with 10X samples
sc_list = ['10X-3prime', '10X-ATAC', '10X-CNV']

# create new csv for just 10X samples
cellranger_10X_df = sample_pd[sample_pd['DataAnalysisType'].isin(sc_list)]
cellranger_idx_list_to_drop = cellranger_10X_df.index.values.tolist()

#combine 10X and iCLIP lists to drop
total_idx_to_drop = idx_list_to_drop + cellranger_idx_list_to_drop

cellranger_needed = 'false'
if len(cellranger_10X_df) > 0:
    with open('10X_samplesheet.10x.csv', 'w+') as fp:
        fp.write('[Data]\n')
        cellranger_10X_df.to_csv(fp, index=False)
        fp.close()
    cellranger_needed = 'true'

x = open(cellranger_needed + ".txt", "w")
x.close()

sample_pd.drop(sample_pd.index[total_idx_to_drop], inplace=True)

with open('reformatted_samplesheet.standard.csv', 'w+') as f:
    f.write('[Data]\n')
    sample_pd.to_csv(f, index=False)
    f.close()