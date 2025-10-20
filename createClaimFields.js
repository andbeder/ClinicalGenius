#!/usr/bin/env node

require('dotenv').config();
const authorize = require('./sfdcJwtAuth');
const { execSync } = require('child_process');

async function createClaimFields() {
  console.log('Authenticating to Salesforce...');
  await authorize();

  const fields = [
    { name: 'Clinical_Summary__c', label: 'Clinical Summary' },
    { name: 'Claim_Summary__c', label: 'Claim Summary' },
    { name: 'Clinical_Review__c', label: 'Clinical Review' },
    { name: 'Expert_Review__c', label: 'Expert Review' }
  ];

  console.log('\nCreating fields on Claim__c object...\n');

  for (const field of fields) {
    try {
      console.log(`Creating field: ${field.label}...`);

      const command = `sf data create record -s FieldDefinition -v "QualifiedApiName='${field.name}' Label='${field.label}' EntityDefinition='Claim__c' DataType='LongTextArea' Length=32768" --json`;

      // Alternative approach using Metadata API via sf project deploy
      const metadataXml = `<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>${field.name}</fullName>
    <label>${field.label}</label>
    <length>32768</length>
    <type>LongTextArea</type>
    <visibleLines>5</visibleLines>
</CustomField>`;

      console.log(`  Using Salesforce CLI to create ${field.name}...`);

      // Use anonymous apex to create the field
      const apex = `
Schema.SObjectField field = Schema.getGlobalDescribe().get('Claim__c').getDescribe().fields.getMap().get('${field.name}');
if (field == null) {
    System.debug('Field ${field.name} does not exist - please create via Metadata API');
}
`;

      execSync(`sf sobject describe -s Claim__c --json`, { encoding: 'utf8' });
      console.log(`  ✓ Verified Claim__c object exists`);

    } catch (err) {
      console.error(`  ✗ Error with ${field.name}:`, err.message);
    }
  }

  console.log('\n⚠ Note: Creating custom fields requires using the Metadata API.');
  console.log('The Salesforce CLI "data create record" command does not support field creation.');
  console.log('\nPlease use one of these approaches:');
  console.log('1. Create fields manually in Salesforce Setup');
  console.log('2. Use SFDX project with metadata deployment');
  console.log('3. Use Salesforce REST Metadata API\n');
}

createClaimFields().catch(err => {
  console.error('Error:', err.message);
  process.exit(1);
});
