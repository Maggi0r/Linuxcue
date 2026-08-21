import QtQuick
import QtQuick.Layouts

GridLayout {
    id: zones
    property string selectedZone: "all"
    signal zonePicked(string zone)

    columns: 2
    rowSpacing: 10
    columnSpacing: 10
    Repeater {
        model: [
            ["custom", "+"], ["all", "Alle"],
            ["wasd", "WASD"], ["qwerdf", "QWERDF"],
            ["gkeys", "G-Tasten"], ["numpad", "Ziffernblock"],
            ["arrows", "Pfeiltasten"], ["numbers", "1-6"]
        ]
        delegate: Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 40
            radius: 6
            color: modelData[0] === "custom" ? "#f5ef00" : zones.selectedZone === modelData[0] ? "#ffffff" : "#2b2b2b"
            Text { anchors.centerIn: parent; text: modelData[1]; color: modelData[0] === "custom" || zones.selectedZone === modelData[0] ? "#111111" : "#8d969b"; font.bold: true; font.pixelSize: 12 }
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    zones.selectedZone = modelData[0]
                    zones.zonePicked(modelData[0])
                }
            }
        }
    }
}
