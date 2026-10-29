/**
 * SPDX-FileCopyrightText: 2026 meatybot
 * SPDX-License-Identifier: MIT
 */

import { apiUrl } from './exapp.js'

async function json(response) {
	const body = await response.json()
	if (!body.ok) {
		throw new Error(body.error || `HTTP ${response.status}`)
	}
	return body
}

/**
 * Templates matching `query`, or the 100 most popular ones for an empty query (their boxes are null).
 *
 * @param {string} query search text
 * @param {AbortSignal} signal aborts the request
 */
export async function searchTemplates(query, signal) {
	return (await json(await fetch(apiUrl(`search?limit=40&q=${encodeURIComponent(query)}`), { signal }))).data
}

/**
 * One template with its text boxes.
 *
 * @param {number} id template ID
 */
export async function getTemplate(id) {
	return (await json(await fetch(apiUrl(`template?id=${id}`)))).data
}

/**
 * Template image through the ExApp: same origin, so the Konva canvas stays exportable.
 *
 * @param {{id: number, file_type: string}} template the template
 */
export const templateImageUrl = (template) => apiUrl(`template-image/${template.id}.${template.file_type}`)

/**
 * Hosts a finished JPEG on imgflip and resolves to `{url, page_url, iid, ...}`.
 *
 * @param {object} payload template_id, image (data URL), texts, boxes
 */
export async function hostMeme(payload) {
	return json(await fetch(apiUrl('upload'), {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(payload),
	}))
}
