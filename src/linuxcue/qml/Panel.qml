import QtQuick

Rectangle {
    property string title: ""

    radius: 14
    clip: true
    gradient: Gradient {
        GradientStop { position: 0.0; color: "#171f22" }
        GradientStop { position: 0.52; color: "#0f1517" }
        GradientStop { position: 1.0; color: "#090d0f" }
    }
    border.color: "#24363d"
    border.width: 1

    Rectangle {
        anchors.fill: parent
        anchors.margins: 1
        radius: parent.radius - 1
        color: "transparent"
        border.color: "#0c171b"
        border.width: 1
    }

    Text {
        text: parent.title
        color: "white"
        font.pixelSize: 16
        font.bold: true
        x: 16
        y: 16
    }
}
