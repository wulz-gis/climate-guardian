#!/usr/bin/env node
/**
 * Migrate lesson JSON files to unified schema conventions.
 *
 * Usage:
 *   node scripts/migrate_lessons.mjs [--write]
 *
 * - Reads JSONs under public/slides/
 * - Normalizes field names and types
 * - Adds missing required fields with safe defaults
 * - Creates backup before overwriting when --write is provided
 *
 * Docstring style follows PEP 257 principles for clarity and completeness.
 */
import fs from 'node:fs'
import path from 'node:path'
import process from 'node:process'

/**
 * Ensure a data path has leading slash for Vite base resolution.
 *
 * Returns a normalized path string like "/assets/data/lesson-05-sample.csv".
 */
function normalizeDataPath(p) {
  if (!p || typeof p !== 'string') return ''
  let s = p.trim()
  if (!s.startsWith('/')) s = '/' + s
  // collapse duplicate slashes globally
  s = s.replace(/\/+/, '/').replace(/\/+/, '/')
  return s
}

/**
 * Migrate a single slide item to unified schema conventions.
 *
 * Applies the following rules:
 * - type "title" -> type "cover", title from content
 * - type "text" with content including "学习目标" -> type "objective", bullets from data
 * - type "text" with content including "思考题" -> type "discussion", questions from question/questions
 * - other "text" -> type "concept", content from body/description or joined data
 * - type "chart": ensure chartType, move data/src/dataSrc to dataSrc and normalize path
 * - type "discussion": fold question -> questions
 * - add default duration if missing (120 seconds)
 */
function migrateSlide(s) {
  const out = { ...s }
  const t = String(s.type || '').trim().toLowerCase()

  if (t === 'title') {
    out.type = 'cover'
    out.title = s.content || s.title || out.title || ''
    delete out.content
  } else if (t === 'text') {
    const contentStr = String(s.content || '').toLowerCase()
    const hasGoals = contentStr.includes('学习目标')
    const hasQuestions = contentStr.includes('思考题')
    if (hasGoals) {
      out.type = 'objective'
      out.title = s.content || out.title || '本课目标'
      const dataList = Array.isArray(s.data) ? s.data : []
      out.bullets = dataList
      delete out.data
    } else if (hasQuestions) {
      out.type = 'discussion'
      out.title = s.content || out.title || '讨论思考'
      const q = Array.isArray(s.questions) ? s.questions : Array.isArray(s.question) ? s.question : []
      out.questions = q
      delete out.question
    } else {
      out.type = 'concept'
      out.title = s.content || out.title || '知识点'
      const body = s.body || s.description || ''
      const dataList = Array.isArray(s.data) ? s.data : []
      out.content = body || (dataList.length ? dataList.join('；') : out.content || '')
      delete out.data
    }
  } else if (t === 'chart') {
    out.chartType = s.chartType || 'line'
    const src = s.dataSrc || s.src || s.data || ''
    out.dataSrc = normalizeDataPath(src)
    delete out.src
    delete out.data
  } else if (t === 'discussion') {
    const q = Array.isArray(s.questions) ? s.questions : Array.isArray(s.question) ? s.question : []
    out.questions = q
    delete out.question
  }

  if (out.duration == null) {
    out.duration = 120
  }

  return out
}

/**
 * Migrate a full lesson JSON object.
 *
 * Ensures root fields and applies slide migrations.
 */
function migrateLesson(json) {
  const out = { ...json }
  if (!out.title) out.title = `未命名课程`
  if (!Array.isArray(out.slides)) out.slides = []
  out.slides = out.slides.map(migrateSlide)
  return out
}

/**
 * Create a timestamped backup alongside original file.
 */
function backupFile(fullPath) {
  const ts = new Date().toISOString().replace(/[-:T.Z]/g, '').slice(0, 14)
  const bak = `${fullPath}.bak-${ts}`
  fs.copyFileSync(fullPath, bak)
  return bak
}

/**
 * Process all JSON files in public/slides.
 *
 * If --write is passed, backups originals and overwrites with migrated JSON.
 */
function main() {
  const slidesDir = path.resolve('public/slides')
  const files = fs.readdirSync(slidesDir).filter(f => f.endsWith('.json'))
  const write = process.argv.includes('--write')

  let changed = 0
  for (const f of files) {
    const full = path.join(slidesDir, f)
    const raw = fs.readFileSync(full, 'utf-8')
    const json = JSON.parse(raw)
    const migrated = migrateLesson(json)
    const outStr = JSON.stringify(migrated, null, 2)
    if (write) {
      const bak = backupFile(full)
      fs.writeFileSync(full, outStr, 'utf-8')
      console.log(`✅ Migrated ${f} (backup: ${path.basename(bak)})`)
      changed++
    } else {
      console.log(`ℹ️ Preview ${f} (no write).`)
    }
  }

  console.log(`\nSummary: processed ${files.length} files, migrated ${changed}.`)
}

// Invoke main entry point.
main()