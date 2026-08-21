import QtQuick

Rectangle {
    property string label: ""
    property string state: ""
    width: 110
    height: 52
    radius: 12
    color: "#0b1514"
    border.color: "#244139"
    Column {
        anchors.centerIn: parent
        spacing: 1
        Text { text: label; color: "white"; font.bold: true; font.pixelSize: 12 }
        Text { text: state; color: "#d7ff37"; font.bold: true; font.pixelSize: 12 }
    }
}
