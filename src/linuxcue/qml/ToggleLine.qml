import QtQuick
import QtQuick.Controls

Row {
    id: row
    property string text: ""
    property bool checked: false
    signal toggled(bool checked)
    spacing: 10
    width: parent ? parent.width : 180
    clip: true
    Text {
        text: row.text
        color: "#8f9da3"
        font.pixelSize: 12
        width: Math.max(88, row.width - 54)
        elide: Text.ElideRight
    }
    Switch {
        checked: row.checked
        scale: 0.58
        onToggled: row.toggled(checked)
    }
}
