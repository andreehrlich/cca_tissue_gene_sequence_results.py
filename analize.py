#####################################
######  	 ABOUT THIS SCRIPY 	    #
#####################################
# This script reads the results of sequenced barcodes of tissue and execute them to an SQLite3 database.
# URL to retreive gene sequencing data for CCA tissue:
# https://tcga-data.nci.nih.gov/tcga/tcgaCancerDetails.jsp?diseaseType=CHOL&diseaseName=Cholangiocarcinoma


#####################################
######  INSTRUCTIONS FOR USE:		#
#####################################
#In the shell go to this directory and type 'python analize.py' to run the script.
# -- It seems to run much faster this way, than to run it in Sublime Text 2, in my experience.
# check out the README for more information..


#####################################
######  SETTING UP 				 	#
#####################################
# this is a library used to read files in
import csv
# these libraries will help us write our info to a database. easiest to read in.
import sqlite3 as lite
import sys
#setting up the outfile for out results!
con = lite.connect('../larry_CCA_analysis/geneSequenceResults.db'); #initilazing output file
cur = con.cursor() #save cursor to var
cur.execute("DROP TABLE IF EXISTS genes") #if this table doesn't exist, create it.
cur.execute("CREATE TABLE genes (geneid text, normcount real, barcode text, tissuetype text)")#vals in each col of table

cur.execute("DROP TABLE IF EXISTS isoforms"); # a second table
cur.execute("CREATE TABLE isoforms (barcode text, geneid text, isoformid text, normcount real)")

# we will fill this Cabinet list with objects of class TissueSample..
cabinet = [] # array will hold TissueSample objects, holding a tissue barcode and it's data.
tissueTypeDict = {}; #this will be the reference for when we find which samples as cancerous... further down.

# file path's are relative to where the py script is saved. so they could cause problems if you aren't lookin the right place.
manifestFile = "../larry_CCA_analysis/TCGA CHOL RNA-seq/file_manifest.txt"; #this is the manifest file path. it has barcode names and filenames.
#append this before each barcode filename so python can find the file.
pathToDataFiles = "../larry_CCA_analysis/TCGA CHOL RNA-seq/RNASeqV2/UNC__IlluminaHiSeq_RNASeqV2/Level_3/"; # where the files are the scientist wants.
filenameKeywords = ["genes.results","genes.normalized","isoforms.normalized"]; # the files scientist wants for his study.
tissue_type_file = "tissuetype.csv"; #file made by scientist.


########################################################
#Reading Samples: Tissue Types. Adding to dictionary.###
########################################################
with open(tissue_type_file, 'rb') as f:
	reader = csv.reader(f, delimiter="\t")
	print "\n\nReading in tissue type, line by line..."
	#print "current case:", currCase, "current tissue:", tissue
	ctr = 0;
	for line in reader:
		print line
		tissueTypeDict[line[0]] = line[1];
		ctr = ctr + 1;
	print "Done!"

tmpList = []; #just preloading. this will be used to populate the db file! see the class
isoCount = 0;

# This is a class definition, an object called TissueSample that will get information using functions, and storing it in its attributes
class TissueSample:
	def __init__(self,barcode): # function initializes class, must pass in a barcode and tissue type.
		self.barcode = barcode;	#see example below class definition
		self.sample = barcode[:15] #the sample is first 15 char, see manifest for example.
		self.tissue_type = tissueTypeDict[self.sample]; #find matching tissue type.
		print "\tFound tissue type:", self.barcode, self.tissue_type, "Added to cabinet!"

	#attributes for the TissueSample. These hold the filenames for data, and will hold data themselves.
	genes_results = {"gene_id":"multiple_transcript_ids", #attribute  with dictionary
					"filepath": ""} #currently set at NULL, and genes_results['filename'] is considered NULL.
	genes_norms = 	{"gene_id":"normalized_count",
					"filepath": ""}
	isoforms_norms = {"isoform_id":"normalized_count", #isoform_id == transcript id from gene.results
						"filepath": ""}
	tissue_type = "none";
# you can add attributes (or attr's) to your cases by defining (or def) functions to input
# learned from: http://sthurlow.com/python/lesson08/

	def filename_function_switch(self, keyword):
		if "genes.normalized" in keyword: #this function should really cycle through all the keywords that are inputted
			self.add_genes_norms(keyword)
		elif "genes.results" in keyword:
			self.add_genes_results(keyword);
		elif "isoforms.normalized" in keyword:
			self.add_isoforms_norms(keyword);

	def add_isoforms_norms(self,filename): #functions to add attribute to the object...
		path = pathToDataFiles + filename;# filename passed from manifest needs it's path prepended.
		self.isoforms_norms['filepath'] = path; 			# so we use functions for the name, but when adding genes
		print "\tAdded filepath."
		with open(path, 'rb') as f: #use the file we read in to get all its necessary contents
			print "\tReading in Isoforms Normalized Results and storing in TissueSample in cabinet."
			reader = csv.reader(f, delimiter="\t")
			for line in reader:
				self.isoforms_norms[line[0]] = line[1] #add this data to the dict attribute above
		if (self.genes_results['filepath']): #both files are GO.
			self.add_isoforms_ids(); #call function to write to DB.


	def add_genes_norms(self,filename):
		path = pathToDataFiles + filename;
		self.genes_norms['filepath'] = path;
		with open(path, 'rb') as f:
			print "\tReading in Genes Normalized Results and executing to DB."
			reader = csv.reader(f, delimiter="\t")
			for line in reader:
				tmpList = [];
				#self.genes_norms[line[0]] = line[1]
				tmpList.extend([line[0],line[1],self.barcode,self.tissue_type]);
				cur.execute('INSERT INTO genes VALUES (?,?,?,?)', tmpList)
		#this is where we will export our fulfilled TissueSample object to a table using sqlite.

	def add_genes_results(self,filename):
		path = pathToDataFiles + filename;
		self.genes_results['filepath'] = path;
		print "\tAdded filepath."
		with open(path, 'rb') as f: #this is using the csv library to read the file into python
			print "\tReading in Gene Results and adding to TissueSample in cabinet"
			reader = csv.reader(f, delimiter="\t") #telling python to read it by every tab or \t
			for line in reader: #we are reading one line of the file at a time, it is a list, or array
				arrayify = line[3].split(",") #arrafiy makes a list out of transcript ids in the 3rd column.
				self.genes_results[line[0]] = arrayify; #this dictionary will have the gene key match to a list of isoforms in the
		if (self.isoforms_norms['filepath']): #other file has been read in, as well! let's go!
			self.add_isoforms_ids(); #write to DB using both necessary files.

	def add_isoforms_ids(self):
		print "\tReading in corresponding Genes and Isoforms IDs, and each iso_id normcount."
		print "\tWriting to Database under table 'isoforms'."
		#the two files compiment each other
		#self.genes_results[line[0]] = arrayify;
		#self.isoforms_norms[line[0]] = line[1] each key corresponds to an index in arrayify..
		for key, val in self.genes_results.iteritems():
			for x in val:
				isoCount = self.isoforms_norms.get(x, None);
				tmpList = [];
				# 				barcode, gene_id. isoform id. isoform count.
				tmpList.extend([self.barcode, key, x, isoCount]);
				cur.execute('INSERT INTO isoforms VALUES (?,?,?,?)', tmpList)

#############################
#Reading in the file_manifest
#############################

fileInCabinet = False; #this boolean is to let us know if we found the barcode name in the cabinet.
importantLine = False; #this boolean is to let us know if the line we read is important!
placeHolder = -1; #if the barcode is in the cabinet, then this number will be it's index.
i = 0; #count lines read by script.

with open(manifestFile, 'rb') as f:
	reader = csv.reader(f, delimiter="\t")
	print "Reading in file_manifest, line by line..."
	for line in reader:
		i = i+1 #update count!
		for name in filenameKeywords:
			if name in line[6]:#remove top 3 rows, and also two quantification filename_barcodes per barcode b/c unnecessary
				print "\nLine", i,"from manifest. barcode:", line[5], "\n\tfilename snippet: ",line[6].split("rsem.",1)[1]
				importantLine = True;
				for l in cabinet: #search the cabinet
					if (line[5] == l.barcode): #the barcode is already in cabinet.
						placeHolder = cabinet.index(l); #find position of the TissueSample
						fileInCabinet = True;
						print "\tFound the TissueSample in cabinet! placeHolder: ", placeHolder
								#this needs to be after the for loop searching cabinet.
								#b/c we search the whole cabinet for the file.
				if (fileInCabinet == True): # the barcode is already there!
					cabinet[placeHolder].filename_function_switch(line[6])
					fileInCabinet = False #now search is done, reset this indicator for next barcode.
				else: #otherwise, the barcode is not in Cabinet.
					x = TissueSample(line[5]) #We make an new instance of the object, with tissue sample.
					x.filename_function_switch(line[6])

					cabinet.append(x) #and add it to the cabinet.
		if (importantLine == True):
			importantLine = False;
		else:
			print "\nLine",i,"does not contain a barcode or proper filename\n"

print "Now printing genes table to console from DB... They have already been printed to geneSequenceResults.db in this directory."
print "\tThis will take about 10-15 minutes... "
									#this is basic mysqlite and it's pretty simple!
cur.execute("SELECT * FROM genes") # you can also select from genes to see the other table!
for row in cur:
	print row

print "Above is the genes table from database printed out to console."
print '-' * 55
print "Now printing isoforms table to console from DB"

cur.execute('SELECT * FROM isoforms')
for row in cur:
	print row

print "Above is the isoforms and genes table from database printed out to console."
print '-' * 55


con.commit() #commit all the additions to our Database. This is what takes so long... i think.
con.close()
