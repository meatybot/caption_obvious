<!--
  - SPDX-FileCopyrightText: 2026 meatybot
  - SPDX-License-Identifier: MIT
-->
<template>
	<div ref="container" class="meme-canvas" />
</template>

<script>
import Konva from 'konva'
import { fontFamily, loadFont } from '../fonts.js'

/**
 * The template with its text boxes, drawn with Konva. Every node uses template pixels; the stage is
 * scaled to fit the available space and exports at full size via pixelRatio.
 * The parent owns the boxes: this component draws them and writes back the geometry the user drags,
 * resizes or rotates.
 */
export default {
	name: 'MemeCanvas',

	props: {
		image: {
			type: HTMLImageElement,
			required: true,
		},
		template: {
			type: Object,
			required: true,
		},
		boxes: {
			type: Array,
			required: true,
		},
		selectedId: {
			type: Number,
			default: null,
		},
		maxWidth: {
			type: Number,
			required: true,
		},
		maxHeight: {
			type: Number,
			required: true,
		},
	},

	emits: ['select', 'update:box', 'font-loaded', 'font-error'],

	watch: {
		boxes: {
			deep: true,
			handler() {
				this.syncNodes()
			},
		},
		selectedId() {
			this.syncSelection()
		},
		maxWidth() {
			this.resize()
		},
		maxHeight() {
			this.resize()
		},
	},

	mounted() {
		const { width, height } = this.template
		this.stage = new Konva.Stage({ container: this.$refs.container, width, height })
		this.layer = new Konva.Layer()
		this.stage.add(this.layer)
		this.background = new Konva.Image({ image: this.image, width, height })
		this.layer.add(this.background)
		const watermarkSize = Math.max(10, width / 45)
		this.layer.add(new Konva.Text({ // imgflip's bottom-left watermark
			text: 'imgflip.com',
			x: 4,
			y: height - watermarkSize - 6,
			fontSize: watermarkSize,
			fontFamily: fontFamily('arial'),
			fill: 'rgba(255,255,255,.9)',
			stroke: 'rgba(0,0,0,.6)',
			strokeWidth: 1,
			fillAfterStrokeEnabled: true,
			listening: false,
		}))
		this.transformer = new Konva.Transformer({ rotateEnabled: true, keepRatio: false, ignoreStroke: true })
		this.layer.add(this.transformer)
		this.stage.on('pointerdown', (e) => {
			if (e.target === this.stage || e.target === this.background) {
				this.$emit('select', null)
			}
		})
		this.nodes = new Map()
		this.resize()
		this.syncNodes()
	},

	beforeUnmount() {
		this.stage?.destroy()
	},

	methods: {
		resize() {
			const { width, height } = this.template
			const scale = Math.min(1, this.maxWidth / width, this.maxHeight / height)
			this.stage.size({ width: width * scale, height: height * scale })
			this.stage.scale({ x: scale, y: scale })
		},

		syncNodes() {
			const ids = new Set(this.boxes.map((box) => box.id))
			for (const [id, entry] of this.nodes) {
				if (!ids.has(id)) {
					entry.text.destroy()
					entry.hint.destroy()
					this.nodes.delete(id)
				}
			}
			for (const box of this.boxes) {
				if (!this.nodes.has(box.id)) {
					this.nodes.set(box.id, this.createNode(box))
				}
				this.fit(box)
				this.ensureFont(box)
			}
			this.transformer.moveToTop()
			this.syncSelection()
		},

		// Downloads the box's font on first use, then fits again with the real glyph metrics.
		ensureFont(box) {
			const entry = this.nodes.get(box.id)
			if (entry.font === box.font) {
				return
			}
			entry.font = box.font
			const font = box.font
			loadFont(font).then(() => {
				// Report every outcome, even if the box moved on to another font meanwhile: the parent tracks
				// loading and failed state per font, and would otherwise keep a stale spinner or warning.
				this.$emit('font-loaded', font)
				if (this.nodes.get(box.id) === entry && entry.font === font) {
					this.fit(box)
					// The attributes may be unchanged (same family string), so Konva would not redraw on its own.
					this.layer.batchDraw()
				}
			}).catch(() => {
				if (entry.font === font) {
					entry.font = null // retry on the next change
				}
				this.$emit('font-error', font)
			})
		},

		/**
		 * Loads `font` again for every box that uses it, after a failed download.
		 *
		 * @param {string} font font ID
		 */
		retryFont(font) {
			for (const box of this.boxes.filter((candidate) => candidate.font === font)) {
				this.nodes.get(box.id).font = null
				this.ensureFont(box)
			}
		},

		createNode(box) {
			const text = new Konva.Text({ draggable: true, wrap: 'word', lineHeight: 1.1, fillAfterStrokeEnabled: true })
			const hint = new Konva.Rect({ listening: false, stroke: 'rgba(80,120,255,.8)', dash: [6, 4], strokeScaleEnabled: false })
			this.layer.add(hint, text)
			text.on('pointerdown', () => this.$emit('select', box.id))
			text.on('dragmove transform', () => this.syncHint(text, hint, !box.text.trim()))
			text.on('dragend', () => this.$emit('update:box', { id: box.id, x: text.x(), y: text.y() }))
			text.on('transformend', () => {
				// Bake the scale into the size, so the text reflows instead of stretching.
				const w = Math.max(20, text.width() * text.scaleX())
				const h = Math.max(20, text.height() * text.scaleY())
				text.setAttrs({ scaleX: 1, scaleY: 1 })
				this.$emit('update:box', { id: box.id, x: text.x(), y: text.y(), w, h, rotation: text.rotation() })
			})
			return { text, hint }
		},

		// Largest font size whose wrapped text fits the box, capped at the template's maximum.
		fit(box) {
			const { text, hint } = this.nodes.get(box.id)
			const content = box.caps ? box.text.toUpperCase() : box.text
			const probe = new Konva.Text({ text: content, width: box.w, wrap: 'word', lineHeight: 1.1, fontFamily: fontFamily(box.font) })
			const words = content.split(/\s+/).filter(Boolean)
			let lo = 6
			let hi = Math.max(6, Math.floor(box.maxSize))
			let size = lo
			while (lo <= hi) {
				const mid = (lo + hi) >> 1
				probe.fontSize(mid)
				const widest = Math.max(0, ...words.map((word) => probe.measureSize(word).width))
				if (probe.height() <= box.h && widest <= box.w) {
					size = mid
					lo = mid + 1
				} else {
					hi = mid - 1
				}
			}
			probe.destroy()
			text.setAttrs({
				x: box.x,
				y: box.y,
				width: box.w,
				height: box.h,
				offsetX: box.w / 2,
				offsetY: box.h / 2,
				rotation: box.rotation,
				text: content,
				fontSize: size,
				fontFamily: fontFamily(box.font),
				fill: box.color,
				stroke: box.outline,
				strokeWidth: Math.max(1, size * 0.12),
				align: box.align,
				verticalAlign: box.valign,
			})
			this.syncHint(text, hint, !box.text.trim())
		},

		syncHint(text, hint, visible) {
			const w = text.width() * text.scaleX()
			const h = text.height() * text.scaleY()
			hint.setAttrs({ x: text.x(), y: text.y(), width: w, height: h, offsetX: w / 2, offsetY: h / 2, rotation: text.rotation(), visible })
		},

		syncSelection() {
			const selected = this.nodes.get(this.selectedId)
			this.transformer.nodes(selected ? [selected.text] : [])
		},

		/**
		 * Full-resolution JPEG of the template with the captions, without editor chrome.
		 */
		exportJpeg() {
			this.transformer.nodes([])
			const hints = [...this.nodes.values()].map(({ hint }) => [hint, hint.visible()])
			hints.forEach(([hint]) => hint.visible(false))
			const url = this.stage.toDataURL({ mimeType: 'image/jpeg', quality: 0.92, pixelRatio: 1 / this.stage.scaleX() })
			hints.forEach(([hint, visible]) => hint.visible(visible))
			this.syncSelection()
			return url
		},
	},
}
</script>

<style scoped lang="scss">
.meme-canvas {
	display: flex;
	justify-content: center;
}
</style>
