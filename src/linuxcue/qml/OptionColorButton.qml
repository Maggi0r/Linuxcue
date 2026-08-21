import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id: root
    property string label: ""
    property string colorValue: "#ffffff"
    signal picked()
    spacing: 4
    Rectangle {
        Layout.alignment: Qt.AlignHCenter
        width: 28
        height: 28
        radius: 14
        color: root.colorValue
        border.color: "#e8f4f0"
        border.width: 2
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: root.picked()
        }
    }
    Text {
        Layout.alignment: Qt.AlignHCenter
        text: root.label
        color: "#9fb2b8"
        font.pixelSize: 11
    }
}
