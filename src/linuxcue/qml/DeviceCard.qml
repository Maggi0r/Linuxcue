import QtQuick
import QtQuick.Controls

Rectangle {
    id: card
    property string title: ""
    property string kind: ""
    property string meta: ""
    property string batteryText: ""
    property string state: ""
    property string slug: ""
    property string imageSource: ""
    property bool wireless: false
    property bool selected: false
    signal clicked()

    radius: 4
    border.width: selected ? 1 : 0
    border.color: "#12e8ff"
    color: selected ? "#454545" : "#121619"

    ToolTip.visible: hoverArea.containsMouse
    ToolTip.delay: 350
    ToolTip.text: title

    MouseArea {
        id: hoverArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: card.clicked()
    }

    Rectangle {
        anchors.fill: parent
        opacity: hoverArea.containsMouse ? 0.18 : 0.0
        color: "#ffffff"
    }

    Image {
        id: deviceImage
        anchors.centerIn: parent
        width: slug === "k95" ? parent.width - 12 : parent.width - 24
        height: parent.height - 14
        source: imageSource !== "" ? imageSource : (slug === "k95" ? "../assets/devices/k95-card.png" : "")
        visible: source !== "" && status === Image.Ready
        fillMode: Image.PreserveAspectFit
        smooth: true
        mipmap: true
    }

    Canvas {
        id: icon
        anchors.centerIn: parent
        width: parent.width - 34
        height: parent.height - 16
        visible: !deviceImage.visible
        onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)
            ctx.lineWidth = 2
            ctx.strokeStyle = selected ? "#12e8ff" : "#7d8589"
            ctx.fillStyle = "#20272b"

            if (slug === "m65") {
                ctx.beginPath()
                ctx.ellipse(width / 2, height / 2, 22, 29, 0, 0, Math.PI * 2)
                ctx.fill()
                ctx.stroke()
                ctx.fillStyle = "#ffcf55"
                ctx.beginPath()
                ctx.moveTo(width / 2, height / 2 + 16)
                ctx.lineTo(width / 2 + 11, height / 2 + 23)
                ctx.lineTo(width / 2 + 4, height / 2 + 8)
                ctx.closePath()
                ctx.fill()
            } else if (slug === "virtuoso-se") {
                ctx.beginPath()
                ctx.arc(width / 2, height / 2 + 3, 30, Math.PI * 1.16, Math.PI * 1.84)
                ctx.stroke()
                roundRect(ctx, width / 2 - 35, height / 2, 20, 25, 8)
                ctx.fill()
                ctx.stroke()
                roundRect(ctx, width / 2 + 15, height / 2, 20, 25, 8)
                ctx.fill()
                ctx.stroke()
                ctx.beginPath()
                ctx.moveTo(width / 2 + 27, height / 2 + 22)
                ctx.lineTo(width / 2 + 52, height / 2 + 29)
                ctx.stroke()
                if (wireless) {
                    ctx.strokeStyle = "#c7d4d6"
                    ctx.lineWidth = 2
                    for (var i = 0; i < 3; i++) {
                        ctx.beginPath()
                        ctx.arc(width / 2 + 44, height / 2 - 18, 7 + i * 7, Math.PI * 1.15, Math.PI * 1.85)
                        ctx.stroke()
                    }
                } else {
                    ctx.strokeStyle = "#c7d4d6"
                    ctx.lineWidth = 2
                    ctx.beginPath()
                    ctx.moveTo(width / 2 + 44, height / 2 - 30)
                    ctx.lineTo(width / 2 + 44, height / 2 - 12)
                    ctx.stroke()
                    ctx.fillRect(width / 2 + 39, height / 2 - 42, 10, 10)
                }
            } else {
                roundRect(ctx, width / 2 - 16, 8, 32, height - 20, 6)
                ctx.fill()
                ctx.stroke()
                ctx.fillStyle = "#d5d9da"
                ctx.fillRect(width / 2 - 10, 0, 20, 12)
                ctx.fillStyle = "#57d967"
                ctx.beginPath()
                ctx.arc(width / 2, height / 2 + 10, 5, 0, Math.PI * 2)
                ctx.fill()
            }
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

    Rectangle {
        width: 10
        height: 10
        radius: 5
        color: "#57d967"
        anchors.right: parent.right
        anchors.rightMargin: 8
        anchors.top: parent.top
        anchors.topMargin: 8
    }

    Rectangle {
        visible: batteryText !== ""
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.rightMargin: 8
        anchors.bottomMargin: 7
        width: batterySmallLabel.implicitWidth + 12
        height: 20
        radius: 10
        color: "#121719"
        border.color: "#d6ff28"
        opacity: 0.96

        Text {
            id: batterySmallLabel
            anchors.centerIn: parent
            text: batteryText
            color: "#d6ff28"
            font.bold: true
            font.pixelSize: 10
        }
    }
}
