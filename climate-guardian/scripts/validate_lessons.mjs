#!/usr/bin/env node
/**
 * Validate lesson JSON files against schemas/lesson.schema.json
 *
 * Usage: npm run validate
 *
 * This script reads all JSON files under public/slides and validates them
 * using Ajv with Draft 2020-12. It prints a clear summary and fails with
 * non-zero exit code if any file is invalid.
 *
 * Docstring follows PEP 257 style for clarity.
 */
import fs from 'node:fs'
import path from 'node:path'
import process from 'node:process'
import Ajv2020 from 'ajv/dist/2020.js'

/**
 * Load JSON schema and compile validator.
 *
 * Returns an Ajv validate function for lesson schema.
 */
function loadValidator() {
  const schemaPath = path.resolve('schemas/lesson.schema.json')
  const schemaRaw = fs.readFileSync(schemaPath, 'utf-8')
  const schema = JSON.parse(schemaRaw)
  const ajv = new Ajv2020({ strict: true, allErrors: true })
  const validate = ajv.compile(schema)
  return validate
}

/**
 * Validate all JSON files in public/slides.
 *
 * Prints per-file status and returns aggregated result.
 */
function validateAll() {
  const slidesDir = path.resolve('public/slides')
  const files = fs.readdirSync(slidesDir).filter(f => f.endsWith('.json'))
  const validate = loadValidator()

  let okCount = 0
  const failures = []

  for (const f of files) {
    const full = path.join(slidesDir, f)
    try {
      const raw = fs.readFileSync(full, 'utf-8')
      const json = JSON.parse(raw)
      const valid = validate(json)
      if (valid) {
        okCount++
        console.log(`✅ ${f} valid`)
      } else {
        const errs = validate.errors?.map(e => `${e.instancePath} ${e.message}`).join('\n') || 'Unknown error'
        console.error(`❌ ${f} invalid:\n${errs}`)
        failures.push({ file: f, errors: validate.errors })
      }
    } catch (err) {
      console.error(`❌ ${f} parse/IO error: ${(err && err.message) || err}`)
      failures.push({ file: f, errors: [{ message: 'parse/IO error' }] })
    }
  }

  console.log(`\nSummary: ${okCount}/${files.length} valid, ${failures.length} invalid.`)
  return { okCount, total: files.length, failures }
}

/**
 * Main entry: run validation and set exit code.
 */
function main() {
  const { failures } = validateAll()
  if (failures.length > 0) {
    console.error('\nSchema validation failed. Please fix the files above.')
    process.exitCode = 1
  } else {
    console.log('\nAll lesson JSON files passed schema validation.')
  }
}

// Invoke main entrypoint to ensure script actually runs when called.
main()