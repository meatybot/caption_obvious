/**
 * SPDX-FileCopyrightText: 2026 meatybot
 * SPDX-License-Identifier: MIT
 */

import { getCSPNonce } from '@nextcloud/auth'
import {
	NcCustomPickerRenderResult,
	registerCustomPickerElement,
	registerWidget,
} from '@nextcloud/vue/functions/registerReference'
import { exAppBaseUrl, PROVIDER_ID } from './exapp.js'

// Same structure as the memegen app. The difference: AppAPI serves this script from the ExApp, so the
// lazy chunks load from the ExApp's base URL (`/exapps/<appid>` with HaRP, the AppAPI proxy otherwise)
// instead of from linkTo(appId, 'js/').
__webpack_nonce__ = getCSPNonce() // eslint-disable-line
__webpack_public_path__ = exAppBaseUrl + '/js/' // eslint-disable-line

registerWidget(PROVIDER_ID, async (el, { richObjectType, richObject, accessible }) => {
	const { createApp } = await import(/* webpackChunkName: "vue-lazy" */'vue')
	const { default: MemeReferenceWidget } = await import(/* webpackChunkName: "reference-lazy" */'./views/MemeReferenceWidget.vue')
	const app = createApp(MemeReferenceWidget, { richObjectType, richObject, accessible })
	app.mixin({ methods: { t, n } })
	app.mount(el)
}, () => {}, { hasInteractiveView: false })

registerCustomPickerElement(PROVIDER_ID, async (el, { providerId, accessible }) => {
	const { createApp } = await import(/* webpackChunkName: "vue-lazy" */'vue')
	const { default: MemeCustomPickerElement } = await import(/* webpackChunkName: "reference-picker-lazy" */'./views/MemeCustomPickerElement.vue')

	const app = createApp(MemeCustomPickerElement, { providerId, accessible })
	app.mixin({ methods: { t, n } })
	app.mount(el)

	return new NcCustomPickerRenderResult(el, app)
}, (_, renderResult) => {
	renderResult.object.unmount()
}, 'full')
