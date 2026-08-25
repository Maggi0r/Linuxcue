import QtQuick
import QtQuick.Controls

Column {
    id: panel
    property string currentColor: "#04ff00"
    signal colorPicked(string color)

    spacing: 12

    Row {
        spacing: 14
        Rectangle {
            width: 28
            height: 28
            radius: 14
            color: currentColor
            border.color: "white"
        }
        Text {
            text: "Farbe"
            color: "white"
            anchors.verticalCenter: parent.verticalCenter
            font.pixelSize: 14
        }
        Button {
            anchors.verticalCenter: parent.verticalCenter
            text: "Keine Farbe"
            onClicked: panel.colorPicked("#000000")
            contentItem: Text {
                text: parent.text
                color: "#d7edf0"
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                font.pixelSize: 12
                font.bold: true
            }
            background: Rectangle {
                radius: 8
                color: "#101719"
                border.color: "#35505a"
            }
        }
    }

    Canvas {
        id: wheel
        width: Math.min(parent.width, 170)
        height: width
        anchors.horizontalCenter: parent.horizontalCenter

        onPaint: {
            var ctx = getContext("2d")
            var cx = width / 2
            var cy = height / 2
            var r = width / 2 - 4
            ctx.clearRect(0, 0, width, height)

            for (var a = 0; a < 360; a += 2) {
                ctx.beginPath()
                ctx.moveTo(cx, cy)
                ctx.arc(cx, cy, r, (a - 90) * Math.PI / 180, (a + 2 - 90) * Math.PI / 180)
                ctx.closePath()
                ctx.fillStyle = panel.hsvToHex(a / 360, 1.0, 1.0)
                ctx.fill()
            }

            var inner = ctx.createRadialGradient(cx, cy, 1, cx, cy, r)
            inner.addColorStop(0.0, "rgba(255,255,255,1)")
            inner.addColorStop(0.58, "rgba(255,255,255,0.22)")
            inner.addColorStop(1.0, "rgba(255,255,255,0)")
            ctx.fillStyle = inner
            ctx.beginPath()
            ctx.arc(cx, cy, r, 0, Math.PI * 2)
            ctx.fill()

            ctx.strokeStyle = "#35494f"
            ctx.lineWidth = 2
            ctx.stroke()

            var marker = panel.colorMarker(currentColor, cx, cy, r)
            ctx.beginPath()
            ctx.arc(marker.x, marker.y, 8, 0, Math.PI * 2)
            ctx.fillStyle = "rgba(0,0,0,0.32)"
            ctx.fill()
            ctx.strokeStyle = "white"
            ctx.lineWidth = 3
            ctx.stroke()
            ctx.beginPath()
            ctx.arc(marker.x, marker.y, 4, 0, Math.PI * 2)
            ctx.strokeStyle = "#071014"
            ctx.lineWidth = 1
            ctx.stroke()
        }

        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: function(mouse) {
                var dx = mouse.x - wheel.width / 2
                var dy = mouse.y - wheel.height / 2
                var angle = Math.atan2(dy, dx) * 180 / Math.PI + 90
                if (angle < 0)
                    angle += 360
                panel.colorPicked(hsvToHex(angle / 360, 0.95, 1.0))
            }
        }
    }

    Text { text: "Deckkraft"; color: "white"; font.pixelSize: 13 }
    Slider { width: parent.width; from: 0; to: 100; value: 100 }

    Row {
        spacing: 7
        Repeater {
            model: ["#ff4c4c", "#e34bdd", "#9c43c9", "#7c65e8", "#3157f5", "#4a8cff", "#28c6d0", "#35e0a5", "#59d94f", "#d7ff37", "#ffca2e", "#ff9433", "#ffffff", "#808080", "#000000"]
            delegate: Rectangle {
                width: 24
                height: 24
                radius: 12
                color: modelData
                border.color: currentColor === modelData ? "#d7ff37" : "#444444"
                border.width: currentColor === modelData ? 3 : 1
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: panel.colorPicked(modelData)
                }
            }
        }
    }

    function hsvToHex(h, s, v) {
        var i = Math.floor(h * 6)
        var f = h * 6 - i
        var p = v * (1 - s)
        var q = v * (1 - f * s)
        var t = v * (1 - (1 - f) * s)
        var r = 0
        var g = 0
        var b = 0
        switch (i % 6) {
        case 0: r = v; g = t; b = p; break
        case 1: r = q; g = v; b = p; break
        case 2: r = p; g = v; b = t; break
        case 3: r = p; g = q; b = v; break
        case 4: r = t; g = p; b = v; break
        case 5: r = v; g = p; b = q; break
        }
        return "#" + toHex(r * 255) + toHex(g * 255) + toHex(b * 255)
    }

    function toHex(value) {
        var text = Math.round(value).toString(16)
        return text.length === 1 ? "0" + text : text
    }

    function colorMarker(hex, cx, cy, radius) {
        var hsv = hexToHsv(hex)
        var angle = hsv.h * Math.PI * 2 - Math.PI / 2
        var distance = Math.max(0.08, hsv.s) * radius * 0.92
        return { "x": cx + Math.cos(angle) * distance, "y": cy + Math.sin(angle) * distance }
    }

    function hexToHsv(hex) {
        if (hex === undefined || hex.length < 7)
            return { "h": 0, "s": 0, "v": 1 }
        var r = parseInt(hex.substring(1, 3), 16) / 255
        var g = parseInt(hex.substring(3, 5), 16) / 255
        var b = parseInt(hex.substring(5, 7), 16) / 255
        var max = Math.max(r, g, b)
        var min = Math.min(r, g, b)
        var d = max - min
        var h = 0
        if (d !== 0) {
            if (max === r)
                h = ((g - b) / d + (g < b ? 6 : 0)) / 6
            else if (max === g)
                h = ((b - r) / d + 2) / 6
            else
                h = ((r - g) / d + 4) / 6
        }
        return { "h": h, "s": max === 0 ? 0 : d / max, "v": max }
    }

    onCurrentColorChanged: wheel.requestPaint()
}
