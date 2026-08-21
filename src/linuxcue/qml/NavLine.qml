import QtQuick
import QtQuick.Layouts

Rectangle {
    id: nav
    property string text: ""
    property bool selected: false
    signal clicked()
    Layout.fillWidth: true
    height: 31
    radius: 5
    clip: true
    color: selected ? "#555555" : "transparent"
    Rectangle { visible: selected; width: 4; height: parent.height; radius: 2; color: "#d7ff37" }
    Text {
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.leftMargin: 16
        anchors.right: parent.right
        anchors.rightMargin: 8
        text: nav.text
        color: "white"
        font.bold: selected
        font.pixelSize: 13
        elide: Text.ElideRight
    }
    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: nav.clicked()
    }
}
