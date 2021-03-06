#!/usr/bin/env python

# Load required modules
import sys, os, argparse, json, datetime
from collections import defaultdict

# Set up the connection to the MongoDB database
from pymongo import MongoClient
from bson.objectid import ObjectId

dbHost = os.getenv("MONGO_HOST") or "localhost"
dbName = os.getenv("MONGO_DB_NAME") or "magi"
client = MongoClient("mongodb://" + dbHost + ":27017/" + dbName)
db = client[dbName]
print "Connected to mongodb://{}:27017/{}".format(dbHost, dbName)

# Parse arguments
def get_parser():
	parser = argparse.ArgumentParser()
	parser.add_argument('-tf', '--transcripts_file', type=str, required=True)
	parser.add_argument('-df', '--domains_files', nargs='*', type=str, required=True)
	parser.add_argument('-af', '--annotations_file', type=str, required=False, default=None)
	parser.add_argument('-tdn', '--transcript_dataset_name', type=str, required=True)
	return parser

def run( args ):
	###########################################################################
	# LOAD THE INPUT DATA                                                     #
	###########################################################################

	# Load the domains file(s)
	transcriptToDomains = defaultdict(lambda : defaultdict(list) )
	for domains_file in args.domains_files:
		with open(domains_file, 'r') as IN:
			arrs = [ l.rstrip().split('\t') for l in IN if not l.startswith('#') ]
			for dataset, transcript, domain_name, domain_start, domain_end in arrs:
				obj = dict(start=int(domain_start), end=int(domain_end), name=domain_name)
				transcriptToDomains[transcript][dataset].append( obj )

	# Load the annotations file (if supplied)
	geneToAnnotations = defaultdict( set )
	if args.annotations_file:
		with open(args.annotations_file, 'r') as IN:
			arrs = [ l.rstrip('\n').split('\t') for l in IN if not l.startswith('#') ]
			for gene, locus, amino_acid, annotation_type, site_group_id in arrs:
				geneToAnnotations[gene].add( (int(locus), amino_acid, annotation_type, site_group_id) )

	# Load the transcripts file
	loaded_annotations = 0
	with open(args.transcripts_file, 'r') as IN:
		arrs = [ l.rstrip().split('\t') for l in IN if not l.startswith('#') ]
		transcripts = []
		for gene, transcript, protein, seq in arrs:
			annotations = []
			for locus, amino_acid, annotation_type, site_group_id in geneToAnnotations[gene]:
				if len(seq) >= locus and seq[locus-1] == amino_acid:
					annotations.append( dict(locus=locus, annotation=annotation_type) )
					loaded_annotations += 1
			transcript_obj = dict(name=transcript, gene=gene, sequence=seq, domains=transcriptToDomains[transcript], annotations=annotations)			
			transcripts.append( transcript_obj )
	print loaded_annotations

	###########################################################################
	# CREATE THE OBJECTS IN MONGO                                             #
	###########################################################################

	# Remove the transcripts that already exist for this dataset, if they exist
	existing_dataset = [ oldDb['_id'] for oldDb in db.transcript_datasets.find(dict(name=args.transcript_dataset_name), {"_id": True}) ]
	if len(existing_dataset) > 0:
		db.transcript_datasets.remove({"_id": existing_dataset[0] })
		db.transcripts.remove({"transcript_dataset_id": existing_dataset[0] })
	
	# Then insert the new objects
	existing_dataset = db.transcript_datasets.insert(dict(name=args.transcript_dataset_name))
	for t in transcripts: t['transcript_dataset_id'] = existing_dataset
	db.transcripts.insert( transcripts )

if __name__ == "__main__": run( get_parser().parse_args(sys.argv[1:]))