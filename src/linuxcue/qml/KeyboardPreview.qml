import QtQuick

Item {
    id: keyboard
    property string accentColor: "#04ff00"
    property var keyColors: ({})
    property string selectedKey: ""
    property var selectedKeys: []
    signal selectionChanged(var keys)

    property real contentScale: Math.min(width / baseW, height / baseH) * 1.09
    property real contentX: (width - baseW * contentScale) / 2
    property real contentY: (height - baseH * contentScale) / 2
    readonly property real baseW: 813
    readonly property real baseH: 301

    Canvas {
        id: overlay
        anchors.fill: parent
        opacity: 1.0

        onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)
            drawKeyboardBody(ctx)
            for (var i = 0; i < keyRects.length; i++) {
                var key = keyRects[i]
                if (shouldDrawOverlay(key))
                    drawKeyOverlay(ctx, key)
            }
            if (dragging) {
                ctx.save()
                ctx.strokeStyle = "#f5ef00"
                ctx.lineWidth = 2
                ctx.setLineDash([6, 5])
                ctx.strokeRect(selectionRect.x, selectionRect.y, selectionRect.w, selectionRect.h)
                ctx.restore()
            }
        }
    }

    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        property real startX: 0
        property real startY: 0

        onPressed: function(mouse) {
            startX = mouse.x
            startY = mouse.y
            dragging = false
            selectionRect = { "x": mouse.x, "y": mouse.y, "w": 0, "h": 0 }
        }

        onPositionChanged: function(mouse) {
            var dx = mouse.x - startX
            var dy = mouse.y - startY
            if (Math.abs(dx) > 4 || Math.abs(dy) > 4)
                dragging = true
            if (dragging) {
                selectionRect = normalizedRect(startX, startY, mouse.x, mouse.y)
                overlay.requestPaint()
            }
        }

        onReleased: function(mouse) {
            if (dragging) {
                selectedKeys = keysInRect(selectionRect)
                selectedKey = selectedKeys.length === 1 ? selectedKeys[0] : ""
                selectionChanged(selectedKeys)
            } else {
                toggleKeyAt(mouse.x, mouse.y)
            }
            dragging = false
            overlay.requestPaint()
        }
    }

    onWidthChanged: overlay.requestPaint()
    onHeightChanged: overlay.requestPaint()
    onAccentColorChanged: overlay.requestPaint()
    onKeyColorsChanged: overlay.requestPaint()
    onSelectedKeyChanged: overlay.requestPaint()
    onSelectedKeysChanged: overlay.requestPaint()

    property var keyRects: buildKeys()
    property bool dragging: false
    property var selectionRect: ({ "x": 0, "y": 0, "w": 0, "h": 0 })

    function buildKeys() {
        var keys = []
        addTopZones(keys)
        keys.push({ "id": "preset", "label": "", "x": 379, "y": 48, "w": 58, "h": 20, "logo": true })
        addRow(keys, 142, 62, [["preset", "P"], ["brightness", "BR"], ["lock", "WL"]], 20, 11, 8)
        keys.push({ "id": "mute", "label": "", "x": 662, "y": 50, "w": 18, "h": 10, "muteIcon": true, "mediaKey": true })
        keys.push({ "id": "vol_wheel", "label": "", "x": 687, "y": 49, "w": 42, "h": 12, "wheel": true })
        addRow(keys, 662, 64, [["stop", "\u23F9"], ["prev", "\u23EE"], ["play", "\u23EF"], ["next", "\u23ED"]], 18, 10, 7)
        addColumn(keys, 18, 78, [["g1", "G1"], ["g2", "G2"], ["g3", "G3"], ["g4", "G4"], ["g5", "G5"], ["g6", "G6"]], 28, 25, 31)
        addRow(keys, 76, 78, [["esc", "ESC"]])
        addRow(keys, 128, 78, [["f1", "F1"], ["f2", "F2"], ["f3", "F3"], ["f4", "F4"]])
        addRow(keys, 277, 78, [["f5", "F5"], ["f6", "F6"], ["f7", "F7"], ["f8", "F8"]])
        addRow(keys, 424, 78, [["f9", "F9"], ["f10", "F10"], ["f11", "F11"], ["f12", "F12"]])
        addRow(keys, 76, 109, [["grave", "^"], ["1", "1"], ["2", "2"], ["3", "3"], ["4", "4"], ["5", "5"], ["6", "6"], ["7", "7"], ["8", "8"], ["9", "9"], ["0", "0"], ["minus", "\u00df"], ["equals", "\u00b4"], ["backspace", "BACK", 44]])
        addRow(keys, 76, 140, [["tab", "TAB", 43], ["q", "Q"], ["w", "W"], ["e", "E"], ["r", "R"], ["t", "T"], ["y", "Y"], ["u", "U"], ["i", "I"], ["o", "O"], ["p", "P"], ["lbracket", "["], ["rbracket", "]"]])
        addRow(keys, 76, 171, [["caps", "CAPS", 51], ["a", "A"], ["s", "S"], ["d", "D"], ["f", "F"], ["g", "G"], ["h", "H"], ["j", "J"], ["k", "K"], ["l", "L"], ["semicolon", ";"], ["quote", "'"], ["backslash", "#"]])
        keys.push({ "id": "enter", "label": "ENTER", "x": 494, "y": 140, "w": 40, "h": 56 })
        addRow(keys, 76, 202, [["lshift", "LSHIFT", 61], ["iso_slash", "<"], ["z", "Z"], ["x", "X"], ["c", "C"], ["v", "V"], ["b", "B"], ["n", "N"], ["m", "M"], ["comma", ","], ["period", "."], ["slash", "/"], ["rshift", "RSHIFT", 72]])
        addRow(keys, 76, 233, [["lctrl", "CTRL", 39], ["lwin", "WIN"], ["lalt", "ALT"], ["space", "SPACE", 180], ["ralt", "ALTGR", 40], ["rwin", "WIN"], ["menu", "MENU"], ["rctrl", "CTRL", 40]])
        addRow(keys, 575, 78, [["printscreen", "PRT"], ["scrolllock", "SCR"], ["pause", "PAU"]])
        addRow(keys, 575, 109, [["insert", "INS"], ["home", "HOME"], ["pageup", "PGUP"]])
        addRow(keys, 575, 140, [["delete", "DEL"], ["end", "END"], ["pagedown", "PGDN"]])
        addRow(keys, 608, 202, [["up", "UP"]])
        addRow(keys, 575, 233, [["left", "LEFT"], ["down", "DOWN"], ["right", "RIGHT"]])
        addRow(keys, 672, 78, [["numlock", "NUM"], ["kp_slash", "/"], ["kp_star", "*"], ["kp_minus", "-"]])
        addRow(keys, 672, 109, [["kp7", "7"], ["kp8", "8"], ["kp9", "9"]])
        keys.push({ "id": "kp_plus", "label": "+", "x": 762, "y": 109, "w": 24, "h": 56 })
        addRow(keys, 672, 140, [["kp4", "4"], ["kp5", "5"], ["kp6", "6"]])
        addRow(keys, 672, 171, [["kp1", "1"], ["kp2", "2"], ["kp3", "3"]])
        keys.push({ "id": "kp_enter", "label": "ENTER", "x": 762, "y": 171, "w": 24, "h": 56 })
        addRow(keys, 672, 202, [["kp0", "0", 47], ["kp_dot", "."]])
        return keys
    }

    function addTopZones(keys) {
        var x = 18
        for (var i = 1; i <= 19; i++) {
            if (i === 9 || i === 10) {
                continue
            }
            if (i === 11)
                x = 460
            keys.push({ "id": "led_topzone" + i, "label": "", "x": x, "y": 21, "w": 28, "h": 4, "topZone": true })
            x += 38
        }
    }

    function addColumn(keys, x, y, values, w, h, step) {
        for (var i = 0; i < values.length; i++)
            keys.push({ "id": values[i][0], "label": values[i][1], "x": x, "y": y + i * step, "w": w, "h": h })
    }

    function addRow(keys, x, y, values, defaultW, defaultH, gap) {
        defaultW = defaultW === undefined ? 24 : defaultW
        defaultH = defaultH === undefined ? 25 : defaultH
        gap = gap === undefined ? 6 : gap
        var cursor = x
        for (var i = 0; i < values.length; i++) {
            var id = values[i][0]
            var label = values[i][1]
            var w = values[i].length > 2 ? values[i][2] : defaultW
            if (id !== "gap")
                keys.push({ "id": id, "label": label, "x": cursor, "y": y, "w": w, "h": defaultH })
            cursor += w + gap
        }
    }

    function drawKeyboardBody(ctx) {
        var body = {
            "x": contentX + 7 * contentScale,
            "y": contentY + 44 * contentScale,
            "w": 792 * contentScale,
            "h": 226 * contentScale
        }
        ctx.save()
        roundRect(ctx, body.x, body.y, body.w, body.h, 12 * contentScale)
        var bodyGradient = ctx.createLinearGradient(body.x, body.y, body.x, body.y + body.h)
        bodyGradient.addColorStop(0, "#2f3634")
        bodyGradient.addColorStop(0.24, "#222827")
        bodyGradient.addColorStop(0.56, "#181d1d")
        bodyGradient.addColorStop(1, "#101414")
        ctx.fillStyle = bodyGradient
        ctx.fill()
        ctx.strokeStyle = "#0a0d0f"
        ctx.lineWidth = Math.max(1, 2 * contentScale)
        ctx.stroke()

        ctx.globalAlpha = 0.34
        ctx.strokeStyle = "#68706d"
        ctx.lineWidth = Math.max(1, contentScale)
        for (var i = 0; i < 22; i++) {
            var y = body.y + (24 + i * 6) * contentScale
            ctx.beginPath()
            ctx.moveTo(body.x + 18 * contentScale, y)
            ctx.lineTo(body.x + body.w - 18 * contentScale, y)
            ctx.stroke()
        }
        ctx.globalAlpha = 1

        ctx.globalAlpha = 0.2
        ctx.fillStyle = "#ffffff"
        ctx.fillRect(body.x + 18 * contentScale, body.y + 20 * contentScale, body.w - 36 * contentScale, 2 * contentScale)
        ctx.globalAlpha = 1

        roundRect(ctx, contentX + 379 * contentScale, contentY + 48 * contentScale, 58 * contentScale, 20 * contentScale, 4 * contentScale)
        ctx.globalAlpha = 0.52
        ctx.fillStyle = colorFor("preset")
        ctx.fill()
        ctx.globalAlpha = 0.78
        ctx.strokeStyle = "#91d5a0"
        ctx.lineWidth = Math.max(1, contentScale)
        ctx.stroke()
        ctx.globalAlpha = 0.88
        ctx.fillStyle = "#d6ffe3"
        ctx.font = "bold " + Math.max(5, Math.round(5.1 * contentScale)) + "px Segoe UI"
        ctx.textAlign = "center"
        ctx.textBaseline = "middle"
        ctx.fillText("CORSAIR", contentX + 408 * contentScale, contentY + 58 * contentScale)
        ctx.globalAlpha = 1
        ctx.restore()
    }

    function scaledRect(key) {
        return {
            "x": contentX + key.x * contentScale,
            "y": contentY + key.y * contentScale,
            "w": key.w * contentScale,
            "h": key.h * contentScale
        }
    }

    function drawKeyOverlay(ctx, key) {
        var rect = scaledRect(key)
        var color = colorFor(key.id)
        var selected = isSelected(key.id)
        if (key.isoEnter) {
            drawIsoEnterOverlay(ctx, key, rect, color, selected)
            return
        }
        ctx.save()
        ctx.globalAlpha = key.logo ? 0.0 : (selected ? 1.0 : key.topZone ? 0.95 : 0.92)
        roundRect(ctx, rect.x, rect.y, rect.w, rect.h, key.topZone ? 2 : 4 * contentScale)
        ctx.fillStyle = color
        ctx.fill()
        if (key.wheel) {
            ctx.globalAlpha = 0.72
            ctx.strokeStyle = "rgba(255,255,255,0.42)"
            ctx.lineWidth = Math.max(1, contentScale)
            for (var marker = 0; marker < 6; marker++) {
                var mx = rect.x + 7 * contentScale + marker * 5.5 * contentScale
                ctx.beginPath()
                ctx.moveTo(mx, rect.y + 2 * contentScale)
                ctx.lineTo(mx, rect.y + rect.h - 2 * contentScale)
                ctx.stroke()
            }
        } else if (key.muteIcon) {
            drawMuteIcon(ctx, rect)
        } else if (!key.topZone && !key.logo) {
            var shine = ctx.createLinearGradient(rect.x, rect.y, rect.x, rect.y + rect.h)
            shine.addColorStop(0, "rgba(255,255,255,0.18)")
            shine.addColorStop(0.55, "rgba(255,255,255,0.03)")
            shine.addColorStop(1, "rgba(0,0,0,0.24)")
            ctx.fillStyle = shine
            ctx.fill()
        }
        ctx.globalAlpha = 1
        if (selected) {
            ctx.strokeStyle = "#f5ef00"
            ctx.lineWidth = 3
            ctx.stroke()
        } else if (key.topZone) {
            ctx.strokeStyle = "rgba(16,255,40,0.35)"
            ctx.lineWidth = 1
            ctx.stroke()
        }
        if (key.label !== "" && !key.topZone) {
            ctx.globalAlpha = 1
            var labelSize = Math.max(7, Math.min(Math.round(9.4 * contentScale), Math.round(rect.w / Math.max(1.7, key.label.length * 0.62))))
            ctx.font = "bold " + labelSize + "px Segoe UI"
            ctx.textAlign = "center"
            ctx.textBaseline = "middle"
            drawReadableLabel(ctx, key.label, rect.x + rect.w / 2, rect.y + rect.h / 2, color, selected)
        }
        ctx.restore()
    }

    function drawMuteIcon(ctx, rect) {
        ctx.save()
        ctx.globalAlpha = 0.96
        ctx.strokeStyle = "#d9ecff"
        ctx.fillStyle = "#d9ecff"
        ctx.lineWidth = Math.max(1, 0.9 * contentScale)
        var cx = rect.x + rect.w * 0.40
        var cy = rect.y + rect.h * 0.50
        var s = Math.max(0.7, contentScale * 0.76)
        ctx.beginPath()
        ctx.moveTo(cx - 5 * s, cy - 2 * s)
        ctx.lineTo(cx - 2 * s, cy - 2 * s)
        ctx.lineTo(cx + 2 * s, cy - 5 * s)
        ctx.lineTo(cx + 2 * s, cy + 5 * s)
        ctx.lineTo(cx - 2 * s, cy + 2 * s)
        ctx.lineTo(cx - 5 * s, cy + 2 * s)
        ctx.closePath()
        ctx.fill()
        ctx.beginPath()
        ctx.moveTo(cx + 5.5 * s, cy - 3.6 * s)
        ctx.lineTo(cx + 9.5 * s, cy + 3.6 * s)
        ctx.moveTo(cx + 9.5 * s, cy - 3.6 * s)
        ctx.lineTo(cx + 5.5 * s, cy + 3.6 * s)
        ctx.stroke()
        ctx.restore()
    }

    function drawIsoEnterOverlay(ctx, key, rect, color, selected) {
        var topH = 25 * contentScale
        var lowerX = rect.x + 16 * contentScale
        var lowerY = rect.y + topH - 1 * contentScale
        var lowerW = rect.w - 16 * contentScale
        var lowerH = rect.h - topH + 1 * contentScale
        ctx.save()
        ctx.globalAlpha = selected ? 1.0 : 0.92
        roundRect(ctx, rect.x, rect.y, rect.w, topH, 4 * contentScale)
        ctx.fillStyle = color
        ctx.fill()
        roundRect(ctx, lowerX, lowerY, lowerW, lowerH, 4 * contentScale)
        ctx.fillStyle = color
        ctx.fill()
        var shine = ctx.createLinearGradient(rect.x, rect.y, rect.x, rect.y + rect.h)
        shine.addColorStop(0, "rgba(255,255,255,0.18)")
        shine.addColorStop(0.55, "rgba(255,255,255,0.03)")
        shine.addColorStop(1, "rgba(0,0,0,0.24)")
        ctx.fillStyle = shine
        roundRect(ctx, rect.x, rect.y, rect.w, topH, 4 * contentScale)
        ctx.fill()
        roundRect(ctx, lowerX, lowerY, lowerW, lowerH, 4 * contentScale)
        ctx.fill()
        ctx.globalAlpha = 1
        if (selected) {
            ctx.strokeStyle = "#f5ef00"
            ctx.lineWidth = 3
            roundRect(ctx, rect.x, rect.y, rect.w, topH, 4 * contentScale)
            ctx.stroke()
            roundRect(ctx, lowerX, lowerY, lowerW, lowerH, 4 * contentScale)
            ctx.stroke()
        }
        ctx.font = "bold " + Math.max(7, Math.round(8.6 * contentScale)) + "px Segoe UI"
        ctx.textAlign = "center"
        ctx.textBaseline = "middle"
        drawReadableLabel(ctx, key.label, lowerX + lowerW / 2, lowerY + lowerH / 2, color, selected)
        ctx.restore()
    }

    function drawReadableLabel(ctx, label, x, y, bgColor, selected) {
        var bright = luminance(bgColor) > 135
        var main = bright ? "#08110f" : "#f5fff7"
        var outline = bright ? "rgba(255,255,255,0.82)" : "rgba(0,0,0,0.86)"
        ctx.globalAlpha = selected ? 1.0 : 0.92
        ctx.fillStyle = outline
        ctx.fillText(label, x - 1, y)
        ctx.fillText(label, x + 1, y)
        ctx.fillText(label, x, y - 1)
        ctx.fillText(label, x, y + 1)
        ctx.fillStyle = main
        ctx.fillText(label, x, y)
    }

    function luminance(hex) {
        if (hex === undefined || hex.length < 7)
            return 0
        var r = parseInt(hex.substring(1, 3), 16)
        var g = parseInt(hex.substring(3, 5), 16)
        var b = parseInt(hex.substring(5, 7), 16)
        return 0.299 * r + 0.587 * g + 0.114 * b
    }

    function colorFor(keyId) {
        var value = keyColors[keyId]
        return value === undefined || value === "" ? accentColor : value
    }

    function shouldDrawOverlay(key) {
        if (isSelected(key.id))
            return true
        var value = keyColors[key.id]
        return value !== undefined && value !== ""
    }

    function isSelected(keyId) {
        for (var i = 0; i < selectedKeys.length; i++) {
            if (selectedKeys[i] === keyId)
                return true
        }
        return selectedKey === keyId
    }

    function toggleKeyAt(x, y) {
        for (var i = keyRects.length - 1; i >= 0; i--) {
            var key = keyRects[i]
            var rect = scaledRect(key)
            if (x >= rect.x && x <= rect.x + rect.w && y >= rect.y && y <= rect.y + rect.h) {
                var next = selectedKeys.slice()
                var index = next.indexOf(key.id)
                if (index >= 0)
                    next.splice(index, 1)
                else
                    next.push(key.id)
                selectedKeys = next
                selectedKey = next.length === 1 ? next[0] : ""
                selectionChanged(next)
                return
            }
        }
        selectedKeys = []
        selectedKey = ""
        selectionChanged([])
    }

    function clearSelection() {
        selectedKeys = []
        selectedKey = ""
        dragging = false
        selectionRect = { "x": 0, "y": 0, "w": 0, "h": 0 }
        selectionChanged([])
        overlay.requestPaint()
    }

    function setSelection(keys, notify) {
        selectedKeys = keys === undefined ? [] : keys.slice()
        selectedKey = selectedKeys.length === 1 ? selectedKeys[0] : ""
        dragging = false
        selectionRect = { "x": 0, "y": 0, "w": 0, "h": 0 }
        if (notify === true)
            selectionChanged(selectedKeys)
        overlay.requestPaint()
    }

    function normalizedRect(x1, y1, x2, y2) {
        return {
            "x": Math.min(x1, x2),
            "y": Math.min(y1, y2),
            "w": Math.abs(x2 - x1),
            "h": Math.abs(y2 - y1)
        }
    }

    function keysInRect(rect) {
        var keys = []
        for (var i = 0; i < keyRects.length; i++) {
            var key = keyRects[i]
            var box = scaledRect(key)
            if (rectIntersects(rect, box))
                keys.push(key.id)
        }
        return keys
    }

    function rectIntersects(a, b) {
        return a.x <= b.x + b.w && a.x + a.w >= b.x && a.y <= b.y + b.h && a.y + a.h >= b.y
    }

    function roundRect(ctx, x, y, w, h, r) {
        ctx.beginPath()
        ctx.moveTo(x + r, y)
        ctx.lineTo(x + w - r, y)
        ctx.quadraticCurveTo(x + w, y, x + w, y + r)
        ctx.lineTo(x + w, y + h - r)
        ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h)
        ctx.lineTo(x + r, y + h)
        ctx.quadraticCurveTo(x, y + h, x, y + h - r)
        ctx.lineTo(x, y + r)
        ctx.quadraticCurveTo(x, y, x + r, y)
    }
}
