/**
 * SPDX-FileCopyrightText: 2026 meatybot
 * SPDX-License-Identifier: MIT
 */

const path = require('path')
// we extend the Nextcloud webpack config, as the memegen app does
const webpackConfig = require('@nextcloud/webpack-vue-config')
const ESLintPlugin = require('eslint-webpack-plugin')

const buildMode = process.env.NODE_ENV
const isDev = buildMode === 'development'
webpackConfig.devtool = isDev ? 'cheap-source-map' : 'source-map'

webpackConfig.stats = {
	colors: true,
	modules: false,
}

// AppAPI serves the ExApp's static files from ex_app/js, at <base url>/js/ (see reference.js).
webpackConfig.output.path = path.resolve(__dirname, 'ex_app', 'js')

// The Nextcloud config inlines fonts into the JS. Emit them as files instead, so each one is downloaded
// only when the editor selects it (src/fonts.js).
webpackConfig.module.rules = webpackConfig.module.rules.map((rule) => String(rule.test).includes('woff')
	? { ...rule, test: /\.(png|jpe?g|gif|svg|eot|ttf)$/ }
	: rule)
webpackConfig.module.rules.push({
	test: /\.woff2?$/,
	type: 'asset/resource',
	generator: { filename: 'fonts/[name].[contenthash:8][ext]' },
})

const appId = 'caption_obvious'
webpackConfig.entry = {
	reference: { import: path.join(__dirname, 'src', 'reference.js'), filename: appId + '-reference.js' },
}

webpackConfig.plugins.push(
	new ESLintPlugin({
		extensions: ['js', 'vue'],
		files: 'src',
		failOnError: !isDev,
		configType: 'eslintrc',
	}),
)

module.exports = webpackConfig
