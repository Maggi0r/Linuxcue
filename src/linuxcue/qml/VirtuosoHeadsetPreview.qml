import QtQuick

Canvas {
    id: preview
    property string accentColor: "#1ecfdf"
    property bool wireless: false

    onPaint: {
        var ctx = getContext("2d")
        ctx.clearRect(0, 0, width, height)
        var cx = width * 0.55
        var cy = height * 0.42
        var scale = Math.min(width / 520, height / 360)

        ctx.save()
        ctx.translate(cx, cy)
        ctx.scale(scale, scale)

        var glow = ctx.createRadialGradient(0, 20, 20, 0, 20, 220)
        glow.addColorStop(0, accentColor + "55")
        glow.addColorStop(0.55, "rgba(18,232,255,0.08)")
        glow.addColorStop(1, "rgba(0,0,0,0)")
        ctx.fillStyle = glow
        ctx.beginPath()
        ctx.arc(0, 20, 220, 0, Math.PI * 2)
        ctx.fill()

        ctx.lineWidth = 18
        ctx.lineCap = "round"
        ctx.strokeStyle = "#23282b"
        ctx.beginPath()
        ctx.arc(0, -4, 120, Math.PI * 1.08, Math.PI * 1.92)
        ctx.stroke()
        ctx.lineWidth = 6
        ctx.strokeStyle = "#4c5458"
        ctx.beginPath()
        ctx.arc(0, -4, 103, Math.PI * 1.1, Math.PI * 1.9)
        ctx.stroke()

        drawCup(ctx, -96, 54, -0.18)
        drawCup(ctx, 86, 54, 0.18)

        ctx.strokeStyle = "#7e8589"
        ctx.lineWidth = 5
        ctx.beginPath()
        ctx.moveTo(102, 104)
        ctx.quadraticCurveTo(142, 126, 154, 168)
        ctx.stroke()
        ctx.fillStyle = "#42484c"
        ctx.beginPath()
        ctx.arc(157, 170, 14, 0, Math.PI * 2)
        ctx.fill()

        ctx.fillStyle = accentColor
        ctx.beginPath()
        ctx.arc(94, 64, 14, 0, Math.PI * 2)
        ctx.fill()
        ctx.fillStyle = "#031014"
        ctx.font = "bold 11px sans-serif"
        ctx.textAlign = "center"
        ctx.fillText("lc", 94, 68)

        if (wireless) {
            ctx.strokeStyle = "#c7d4d6"
            ctx.lineWidth = 3
            for (var i = 0; i < 3; i++) {
                ctx.beginPath()
                ctx.arc(154, -106, 12 + i * 13, Math.PI * 1.18, Math.PI * 1.82)
                ctx.stroke()
            }
        } else {
            ctx.strokeStyle = "#c7d4d6"
            ctx.lineWidth = 4
            ctx.beginPath()
            ctx.moveTo(148, -122)
            ctx.lineTo(148, -94)
            ctx.stroke()
            ctx.fillStyle = "#c7d4d6"
            ctx.fillRect(140, -139, 16, 18)
        }

        ctx.restore()
    }

    function drawCup(ctx, x, y, rotation) {
        ctx.save()
        ctx.translate(x, y)
        ctx.rotate(rotation)
        var body = ctx.createLinearGradient(-36, -54, 36, 72)
        body.addColorStop(0, "#444b4f")
        body.addColorStop(0.35, "#15191b")
        body.addColorStop(1, "#050708")
        ctx.fillStyle = body
        roundRect(ctx, -38, -56, 76, 120, 28)
        ctx.fill()
        ctx.strokeStyle = "#5b6266"
        ctx.lineWidth = 4
        ctx.stroke()
        ctx.fillStyle = "#0b0d0e"
        roundRect(ctx, -24, -38, 48, 78, 20)
        ctx.fill()
        ctx.restore()
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

    onAccentColorChanged: requestPaint()
    onWirelessChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
}
