import QtQuick
import QtQuick.Layouts

Rectangle {
    id: layer
    property string layerId: ""
    property string title: ""
    property string colorValue: "#04ff00"
    property bool selected: false
    signal clicked(string layerId)
    signal rightClicked(string layerId, string title)
    Layout.fillWidth: true
    height: 28
    radius: 4
    color: selected ? "#4c4c4c" : "transparent"
    Rectangle { x: 6; anchors.verticalCenter: parent.verticalCenter; width: 18; height: 18; radius: 3; color: colorValue; border.color: "white"; border.width: colorValue === "#ffffff" ? 1 : 0 }
    Text { x: 34; anchors.verticalCenter: parent.verticalCenter; text: title; color: "white"; font.pixelSize: 12 }

    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onClicked: function(mouse) {
            if (mouse.button === Qt.LeftButton)
                layer.clicked(layer.layerId)
            if (mouse.button === Qt.RightButton)
                layer.rightClicked(layer.layerId, layer.title)
        }
    }
}
