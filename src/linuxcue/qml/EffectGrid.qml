import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id: grid
    property bool presetsOpen: true
    property bool customOpen: true
    property string selectedEffect: ""
    signal effectPicked(string effect)

    spacing: 11

    RowLayout {
        Layout.fillWidth: true
        Text {
            Layout.fillWidth: true
            text: "VOREINSTELLUNGEN"
            color: "#7f8d93"
            font.pixelSize: 11
            font.bold: true
        }
        Text {
            text: grid.presetsOpen ? "^" : "v"
            color: "#9aa4aa"
            font.pixelSize: 16
        }
        MouseArea {
            anchors.fill: parent
            onClicked: grid.presetsOpen = !grid.presetsOpen
        }
    }

    GridLayout {
        Layout.fillWidth: true
        visible: grid.presetsOpen
        columns: 3
        rowSpacing: 10
        columnSpacing: 10

        Repeater {
            model: [
                ["Aquarell", "*"], ["Wasserfarben", "*"], ["Farbpulse", "~"],
                ["Farbwechsel", "oo"], ["Farbwelle", "n"], ["CORSAIR Audio", "sp"],
                ["Horizont", "_"], ["Regen", "o"], ["Regenbogen", "rb"],
                ["Spiralregen", "sr"], ["Tastenbeleuchtung", "kb"], ["Visier", "|>"]
            ]

            delegate: Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 40
                radius: 8
                color: grid.selectedEffect === modelData[0] ? "#f3f4ef" : "#2a2d2f"
                border.color: grid.selectedEffect === modelData[0] ? "#ffffff" : "#33383c"

                Text {
                    anchors.centerIn: parent
                    text: modelData[1]
                    color: grid.selectedEffect === modelData[0] ? "#101417" : "#dce5e7"
                    font.pixelSize: 15
                    font.bold: true
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    y: parent.height + 4
                    text: modelData[0]
                    color: "#9aa4aa"
                    font.pixelSize: 10
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    elide: Text.ElideRight
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        grid.selectedEffect = modelData[0]
                        grid.effectPicked(modelData[0])
                    }
                }
            }
        }
    }

    RowLayout {
        Layout.fillWidth: true
        Text {
            Layout.fillWidth: true
            text: "BENUTZERDEFINIERT"
            color: "#7f8d93"
            font.pixelSize: 11
            font.bold: true
        }
        Text {
            text: grid.customOpen ? "^" : "v"
            color: "#9aa4aa"
            font.pixelSize: 16
        }
        MouseArea {
            anchors.fill: parent
            onClicked: grid.customOpen = !grid.customOpen
        }
    }

    GridLayout {
        Layout.fillWidth: true
        visible: grid.customOpen
        columns: 3
        rowSpacing: 10
        columnSpacing: 10

        Repeater {
            model: [
                ["Gradient", "|||"], ["Kraeuseln", "◎"], ["Voll", "o+"],
                ["Statische Farbe", "◎"], ["Welle", "~~~"]
            ]

            delegate: Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 40
                radius: 8
                color: grid.selectedEffect === modelData[0] ? "#f3f4ef" : "#2a2d2f"
                border.color: grid.selectedEffect === modelData[0] ? "#ffffff" : "#33383c"

                Text {
                    anchors.centerIn: parent
                    text: modelData[1]
                    color: grid.selectedEffect === modelData[0] ? "#101417" : "#dce5e7"
                    font.pixelSize: 15
                    font.bold: true
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    y: parent.height + 4
                    text: modelData[0]
                    color: "#9aa4aa"
                    font.pixelSize: 10
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    elide: Text.ElideRight
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        grid.selectedEffect = modelData[0]
                        grid.effectPicked(modelData[0])
                    }
                }
            }
        }
    }

    RowLayout {
        Layout.fillWidth: true
        Text {
            Layout.fillWidth: true
            text: "BELEUCHTUNGSVERKNUEPFUNG"
            color: "#7f8d93"
            font.pixelSize: 11
            font.bold: true
            elide: Text.ElideRight
        }
        Text { text: "v"; color: "#9aa4aa"; font.pixelSize: 16 }
    }
}
