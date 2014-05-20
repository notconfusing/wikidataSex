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

import java.io.FileWriter;
import java.io.IOException;
import java.io.Writer;
import java.util.HashMap;
import java.util.List;

import org.hamcrest.core.IsInstanceOf;
import org.json.JSONObject;
import org.wikidata.wdtk.datamodel.interfaces.EntityDocumentProcessor;
import org.wikidata.wdtk.datamodel.interfaces.ItemDocument;
import org.wikidata.wdtk.datamodel.interfaces.PropertyDocument;
import org.wikidata.wdtk.datamodel.interfaces.Snak;
import org.wikidata.wdtk.datamodel.interfaces.ValueSnak;
import org.wikidata.wdtk.datamodel.interfaces.Statement;
import org.wikidata.wdtk.datamodel.interfaces.StatementGroup;
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
public class sexRatioProcessingExample {

	public static void main(String[] args) throws IOException {

		// Define where log messages go
		ExampleHelpers.configureLogging();

		// Print information about this program
		printDocumentation();

		// Controller object for processing dumps:
		DumpProcessingController dumpProcessingController = new DumpProcessingController(
				"wikidatawiki");
		// // Work offline (using only previously fetched dumps):
		 dumpProcessingController.setOfflineMode(true);
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

		// Start processing (may trigger downloads where needed)
		dumpProcessingController.processAllRecentRevisionDumps();

		// // Process just a recent daily dump for testing:
		// dumpProcessingController.processMostRecentDailyDump();
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
	 * statistics that are printed to the standard output. This could be
	 * replaced with any other class that processes entity documents in some
	 * way.
	 * 
	 * @author Markus Kroetzsch
	 * 
	 */
	static class ItemStatisticsProcessor implements EntityDocumentProcessor {

		long countItems = 0;
		
		HashMap<String,Integer> lang_sexes = new HashMap<String,Integer>(); 


		@Override
		public void processItemDocument(ItemDocument itemDocument) {
			this.countItems++;
			for (StatementGroup sg : itemDocument.getStatementGroups()) {
				for (Statement si: sg.getStatements()) {
					String PID = si.getClaim().getMainSnak().getPropertyId().getId().toString();
					if (PID.equals("P21")) {
						for (String lang_string : itemDocument.getSiteLinks().keySet()) { 
							/* should do this a better way at some point, see
							https://github.com/Wikidata/Wikidata-Toolkit/issues/71#issuecomment-43311843
							Snak main_snak = si.getClaim().getMainSnak();
							if (IsInstanceOf(main_snak, ValueSnak){
								ValueSnak value_snak = new ValueSnakmain_snak);
							}
							*/
							
							String ms = si.getClaim().getMainSnak().toString();
							String[] parts = ms.split("http://www.wikidata.org/wiki/Wikidata:Main_Page/");
							String VID = parts[2].substring(0, parts[2].length()-1);
							String lang_sex_key = lang_string + "--" + VID;
							if (this.lang_sexes.get(lang_sex_key) != null ) {
								this.lang_sexes.put(lang_sex_key, this.lang_sexes.get(lang_sex_key) + 1 );
							}
							else{
								this.lang_sexes.put(lang_sex_key, 1);
							}
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
			JSONObject json_lang_sexes = new JSONObject(this.lang_sexes);
			Writer fwriter = null;
			try {
				fwriter = new FileWriter("/home/notconfusing/workspace/wdtk-parent/wdtk-examples/lang_sex.json");
				json_lang_sexes.write(fwriter);
				fwriter.close();
			} catch (IOException e) {
				// TODO Auto-generated catch block
				e.printStackTrace();
			}
			printReport(); // print a final report
			
		}

		/**
		 * Prints a report about the statistics gathered so far.
		 */
		private void printReport() {
			System.out.println("Processed " + this.countItems + " items:");
			System.out.println("Sex dict" + this.lang_sexes.size());
		}

	}
}
