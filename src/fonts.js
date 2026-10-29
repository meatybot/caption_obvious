/**
 * SPDX-FileCopyrightText: 2026 meatybot
 * SPDX-License-Identifier: MIT
 */

// Fonts of the editor. System fonts come from the user's device. Web fonts are npm packages
// (@fontsource, latin subset, weight 400); webpack emits each .woff2 as its own file, and a font is
// downloaded only when a box uses it. Nextcloud's CSP allows fonts from its own origin only, and the
// ExApp serves them from there, so Google's font CDN is not used.

// `url` is resolved by webpack; the file is fetched only when FontFace.load() runs.
const WEB = [
	{ id: 'anton', label: 'Anton', url: new URL('@fontsource/anton/files/anton-latin-400-normal.woff2', import.meta.url) },
	{ id: 'bebas-neue', label: 'Bebas Neue', url: new URL('@fontsource/bebas-neue/files/bebas-neue-latin-400-normal.woff2', import.meta.url) },
	{ id: 'oswald', label: 'Oswald', url: new URL('@fontsource/oswald/files/oswald-latin-400-normal.woff2', import.meta.url) },
	{ id: 'bangers', label: 'Bangers', url: new URL('@fontsource/bangers/files/bangers-latin-400-normal.woff2', import.meta.url) },
	{ id: 'permanent-marker', label: 'Permanent Marker', url: new URL('@fontsource/permanent-marker/files/permanent-marker-latin-400-normal.woff2', import.meta.url) },
	{ id: 'comic-neue', label: 'Comic Neue', url: new URL('@fontsource/comic-neue/files/comic-neue-latin-400-normal.woff2', import.meta.url) },
	{ id: 'roboto', label: 'Roboto', url: new URL('@fontsource/roboto/files/roboto-latin-400-normal.woff2', import.meta.url) },
	{ id: 'montserrat', label: 'Montserrat', url: new URL('@fontsource/montserrat/files/montserrat-latin-400-normal.woff2', import.meta.url) },
].map((font) => ({
	...font,
	// A family name of our own, so it never clashes with a copy of the font installed on the device.
	face: `CaptionObvious ${font.label}`,
	family: `"CaptionObvious ${font.label}", sans-serif`,
}))

const SYSTEM = [
	// Impact is missing on most Linux systems, so the bundled Anton follows it in the family list.
	{ id: 'impact', label: 'Impact', family: `Impact, impac, ${WEB[0].family}`, web: 'anton' },
	{ id: 'arial', label: 'Arial', family: 'Arial, "Liberation Sans", Helvetica, sans-serif' },
]

export const FONTS = [...SYSTEM, ...WEB]

const byId = Object.fromEntries(FONTS.map((font) => [font.id, font]))

export const fontFamily = (id) => (byId[id] ?? byId.impact).family

export const isKnownFont = (id) => id in byId

const loads = new Map()
const loaded = new Set()

/**
 * Whether `id` can be drawn without a download: system fonts, and web fonts already loaded.
 *
 * @param {string} id font ID
 */
export function isFontLoaded(id) {
	const font = byId[id]
	return !font || loaded.has(font.web ?? id) || (!font.url && !font.web)
}

/**
 * Makes the font of `id` usable on a canvas: downloads a web font once, on first use, and resolves
 * when it is ready. System fonts resolve at once, except Impact, whose bundled Anton fallback is loaded.
 *
 * @param {string} id font ID
 */
export function loadFont(id) {
	const font = byId[id]
	if (!font) {
		return Promise.resolve()
	}
	if (!font.url) {
		return font.web ? loadFont(font.web) : Promise.resolve()
	}
	if (!loads.has(id)) {
		const face = new FontFace(font.face, `url(${font.url.href}) format('woff2')`)
		loads.set(id, face.load().then((face) => {
			document.fonts.add(face)
			loaded.add(id)
		}).catch((error) => {
			loads.delete(id) // let a later selection retry
			throw error
		}))
	}
	return loads.get(id)
}
