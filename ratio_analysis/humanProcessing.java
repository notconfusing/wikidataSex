package org.wikidata.wdtk.examples;

/*
 * #%L
 * Wikidata Toolkit Examples
 * %%
 * Copyright (C) 2014 Wikidata Toolkit Developers
 * %%
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 * 
 *      http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 * #L%
 */

import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.PrintStream;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Set;
import java.util.Map.Entry;

import org.wikidata.wdtk.datamodel.interfaces.Claim;
import org.wikidata.wdtk.datamodel.interfaces.EntityDocumentProcessor;
import org.wikidata.wdtk.datamodel.interfaces.EntityIdValue;
import org.wikidata.wdtk.datamodel.interfaces.ItemDocument;
import org.wikidata.wdtk.datamodel.interfaces.PropertyDocument;
import org.wikidata.wdtk.datamodel.interfaces.PropertyIdValue;
import org.wikidata.wdtk.datamodel.interfaces.Reference;
import org.wikidata.wdtk.datamodel.interfaces.Snak;
import org.wikidata.wdtk.datamodel.interfaces.SnakGroup;
import org.wikidata.wdtk.datamodel.interfaces.Statement;
import org.wikidata.wdtk.datamodel.interfaces.StatementGroup;
import org.wikidata.wdtk.datamodel.interfaces.ValueSnak;
import org.wikidata.wdtk.dumpfiles.DumpProcessingController;
import org.wikidata.wdtk.dumpfiles.MwRevision;
import org.wikidata.wdtk.dumpfiles.MwRevisionProcessor;
import org.wikidata.wdtk.dumpfiles.StatisticsMwRevisionProcessor;

/**
 * This class demonstrates how to write an application that downloads and
 * processes dumpfiles from Wikidata.org.
 * 
 * @author Markus Kroetzsch
 * 
 */
public class humanProcessing {

	public static void main(String[] args) throws IOException {

		// Define where log messages go
		//ExampleHelpers.configureLogging();

		// Print information about this program
		printDocumentation();

		// Controller object for processing dumps:
		DumpProcessingController dumpProcessingController = new DumpProcessingController(
				"wikidatawiki");
		// // Work offline (using only previously fetched dumps):
		// dumpProcessingController.setOfflineMode(true);
		// // Use any download directory:
		// dumpProcessingController.setDownloadDirectory(System.getProperty("user.dir"));

		// Our local example class ItemStatisticsProcessor counts the number of
		// labels etc. in Wikibase item documents to print out some statistics:
		EntityDocumentProcessor edpItemStats = new ItemStatisticsProcessor();
		// Subscribe to the most recent entity documents of type wikibase item:
		dumpProcessingController.registerEntityDocumentProcessor(edpItemStats,
				MwRevision.MODEL_WIKIBASE_ITEM, true);

		// General statistics and time keeping:
		MwRevisionProcessor rpRevisionStats = new StatisticsMwRevisionProcessor(
				"revision processing statistics", 10000);
		// Subscribe to all current revisions (null = no filter):
		dumpProcessingController.registerMwRevisionProcessor(rpRevisionStats,
				null, true);

		// Start processing (may trigger downloads where needed):

		// Process all recent dumps (including daily dumps as far as avaiable)
		dumpProcessingController.processAllRecentRevisionDumps();
		// // Alternatively: Process just a recent daily dump (for testing):
		// dumpProcessingController.processMostRecentDailyDump();
		// // Alternatively: Process just the most recent main dump:
		// dumpProcessingController.processMostRecentMainDump();
	}

	/**
	 * Print some basic documentation about this program.
	 */
	private static void printDocumentation() {
		System.out
				.println("********************************************************************");
		System.out.println("*** Wikidata Toolkit: Dump Processing Example");
		System.out.println("*** ");
		System.out
				.println("*** This program will download and process dumps from Wikidata.");
		System.out
				.println("*** It will print progress information and some simple statistics.");
		System.out
				.println("*** Downloading may take some time initially. After that, files");
		System.out
				.println("*** are stored on disk and are used until newer dumps are available.");
		System.out
				.println("*** You can delete files manually when no longer needed (see ");
		System.out
				.println("*** message below for the directory where files are found).");
		System.out
				.println("********************************************************************");
	}

	/**
	 * A simple example class that processes EntityDocuments to compute basic
	 * statistics that are printed to the standard output. Moreover, that shows
	 * how often certain properties are used in the data. This CSV file is
	 * stored under the name property-counts.csv.
	 * <p>
	 * This could be replaced with any other class that processes entity
	 * documents in some way.
	 * 
	 * @author Markus Kroetzsch
	 * 
	 */
	static class ItemStatisticsProcessor implements EntityDocumentProcessor {

		long countItems = 0;
		long countP31Items = 0;
		long countP31_5Items = 0;
		long countP31_5_24langsItems = 0;
		
		Set<String> langs24 = new HashSet<String>
		(Arrays.asList("enwiki",  "nlwiki",  "dewiki",  "frwiki",  "eswiki",  "itwiki",  "ptwiki",  "elwiki",  "dawiki",  "svwiki",  "plwiki",  "huwiki",  "ruwiki",  "hewiki",  "trwiki",  "arwiki",  "fawiki",  "hiwiki",  "mswiki",  "thwiki",  "viwiki",  "zhwiki",  "kowiki",  "jawiki"));
		
		
		private Boolean inLangs24(Set incomingKeySet){
			Set<String> intersection = new HashSet<String>(langs24);
			intersection.retainAll(incomingKeySet);
			if (intersection.isEmpty()){
				return false;
			}
			else{return true;}
		}
		

		@Override
		public void processItemDocument(ItemDocument itemDocument) {
			this.countItems++;
			
			for (StatementGroup sg : itemDocument.getStatementGroups()) {
				for (Statement si: sg.getStatements()) {
					String PID = si.getClaim().getMainSnak().getPropertyId().getId().toString();
					if (PID.equals("P31")) {
						this.countP31Items++;
						try{
						ValueSnak vs = (ValueSnak) si.getClaim().getMainSnak();
						String VID = vs.getValue().toString();
						if (VID.equals("(ItemId)http://www.wikidata.org/entity//Q5")){
							this.countP31_5Items++;
							if (inLangs24(itemDocument.getSiteLinks().keySet())){
								this.countP31_5_24langsItems++;
							}
						}
						}
						catch(java.lang.ClassCastException castE){
							System.out.println("some error herer");
						}
						}
					}
				}


			// print a report every 10000 items:
			if (this.countItems % 10000 == 0) {
				printReport();
				}
			}

		@Override
		public void processPropertyDocument(PropertyDocument propertyDocument) {
			// ignore properties
			// (in fact, the above code does not even register the processor for
			// receiving properties)
		}

		@Override
		public void finishProcessingEntityDocuments() {
			printReport(); // print a final report
			System.out.println("Finito");
		}

		/**
		 * Prints a report about the statistics gathered so far.
		 */
		private void printReport() {
			System.out.println("Processed " + this.countItems + " items:");
			System.out.println("Processed " + this.countP31Items + " P31 items:");			
			System.out.println("Processed " + this.countP31_5Items + " P31 items with Q5:");			
			System.out.println("Processed " + this.countP31_5_24langsItems + " P31 items with Q5 and in 24langs:");	
		}
	}
}
