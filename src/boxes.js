/**
 * SPDX-FileCopyrightText: 2026 meatybot
 * SPDX-License-Identifier: MIT
 */

import { isKnownFont } from './fonts.js'

// imgflip's font_max_size is relative to a 500px-wide editor.
const EDITOR_WIDTH = 500

let nextId = 1

/**
 * A text box of the editor, from one of imgflip's saved boxes. Geometry is in template pixels,
 * with x/y at the centre so rotation turns around the centre, as on imgflip.
 *
 * @param {object} box imgflip box: x, y, w, h, rotation, font, font_color, outline_color, ...
 * @param {number} templateWidth template width in pixels
 */
export function boxFromTemplate(box, templateWidth) {
	return {
		id: nextId++,
		text: '',
		font: isKnownFont(box.font) ? box.font : 'impact',
		color: box.font_color || '#ffffff',
		outline: box.outline_color || '#000000',
		caps: !!box.force_caps,
		align: box.text_align || 'center',
		valign: box.vertical_align || 'middle',
		maxSize: (box.font_max_size || 50) * (templateWidth / EDITOR_WIDTH) * 1.32,
		x: box.x + box.w / 2,
		y: box.y + box.h / 2,
		w: box.w,
		h: box.h,
		rotation: box.rotation || 0,
	}
}

/**
 * A new box in the middle of the template, for "Add text box".
 *
 * @param {{width: number, height: number}} template the template
 */
export function newBox(template) {
	return boxFromTemplate({
		x: template.width * 0.1,
		y: template.height * 0.4,
		w: template.width * 0.8,
		h: template.height * 0.2,
		font: 'impact',
		force_caps: true,
	}, template.width)
}

/**
 * The box in imgflip's upload format: top-left corner, unrotated.
 *
 * @param {object} box editor box
 */
export function boxForUpload(box) {
	return { type: 'text', x: box.x - box.w / 2, y: box.y - box.h / 2, w: box.w, h: box.h }
}
