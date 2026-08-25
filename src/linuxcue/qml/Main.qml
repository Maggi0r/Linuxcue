import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ApplicationWindow {
    id: window
    width: 1540
    height: 930
    minimumWidth: 1180
    minimumHeight: 760
    visible: true
    title: "linuxcue Studio QML"
    color: "#070c10"
    flags: Qt.Window | Qt.WindowTitleHint | Qt.WindowSystemMenuHint | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint

    property string selectedColor: "#04ff00"
    property bool autoLiveWrite: true
    property int resizeStartX: 0
    property int resizeStartY: 0
    property int resizeStartWidth: width
    property int resizeStartHeight: height
    property string contextProfileName: ""
    property string contextLayerId: ""
    property string contextLayerTitle: ""
    property string contextM65DpiPresetId: ""
    property string contextM65DpiPresetName: ""
    property bool contextM65DpiPresetDefault: false
    property string copiedSelectionTarget: ""
    property bool showK95EffectPicker: false
    property string k95SelectedEffect: ""
    property string k95SelectedQuickZone: "all"
    property string k95SelectedKey: ""
    property var k95SelectedKeys: []
    property bool k95HasSelection: false
    property string k95EditingLayerId: ""
    property string k95Section: "lighting"
    property string m65Section: "lighting"
    property string m65SelectedZone: "all"
    property string m65SelectedColor: "#04ff00"
    property string virtuosoSection: "lighting"
    property string pendingLiveWriteProfile: ""
    property bool contextProfileProtected: false
    property bool showK95Dashboard: linuxcue.currentDevice === "k95"
    property bool showM65Dashboard: linuxcue.currentDevice === "m65"
    property bool showVirtuosoDashboard: linuxcue.currentDevice === "virtuoso-se"

    function clearK95Selection() {
        k95SelectedKeys = []
        k95SelectedKey = ""
        k95SelectedQuickZone = "all"
        k95HasSelection = false
        showK95EffectPicker = false
        k95SelectedEffect = ""
        k95EditingLayerId = ""
    }

    function exitK95LayerEdit() {
        clearK95Selection()
        k95KeyboardPreview.clearSelection()
    }

    function resetDeviceViews() {
        clearK95Selection()
        if (typeof k95KeyboardPreview !== "undefined")
            k95KeyboardPreview.clearSelection()
        k95Section = "lighting"
        m65Section = "lighting"
        m65SelectedZone = "all"
        m65SelectedColor = "#04ff00"
        contextM65DpiPresetId = ""
        contextM65DpiPresetName = ""
        contextM65DpiPresetDefault = false
        virtuosoSection = "lighting"
    }

    function activeVirtuosoPresetName() {
        for (var i = 0; i < linuxcue.virtuosoPresets.length; i++) {
            if (linuxcue.virtuosoPresets[i].selected)
                return linuxcue.virtuosoPresets[i].name
        }
        return linuxcue.virtuosoPresets.length > 0 ? linuxcue.virtuosoPresets[0].name : "Custom"
    }

    function activeVirtuosoPresetIndex() {
        for (var i = 0; i < linuxcue.virtuosoPresets.length; i++) {
            if (linuxcue.virtuosoPresets[i].selected)
                return i
        }
        return 0
    }

    function sleepTimerIndex(value) {
        var values = [5, 10, 20, 30, 60]
        var found = values.indexOf(value)
        return found >= 0 ? found : 2
    }

    function m65ZoneColor(zone) {
        if (zone === "all")
            return m65SelectedColor
        for (var i = 0; i < linuxcue.m65LightingZones.length; i++) {
            if (linuxcue.m65LightingZones[i].name === zone)
                return linuxcue.m65LightingZones[i].color
        }
        return "#04ff00"
    }

    Timer {
        id: hotplugRefreshTimer
        interval: 8000
        running: true
        repeat: true
        onTriggered: linuxcue.refresh()
    }

    Timer {
        id: profileLiveWriteTimer
        interval: 250
        repeat: false
        onTriggered: linuxcue.writeLive()
    }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#111b22" }
            GradientStop { position: 0.45; color: "#081116" }
            GradientStop { position: 1.0; color: "#030607" }
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            id: sidebar
            Layout.preferredWidth: 292
            Layout.fillHeight: true
            color: "#0a1216"
            border.color: "#14252d"

            DropArea {
                id: profileDropArea
                anchors.fill: parent
                keys: ["text/uri-list"]
                onDropped: function(drop) {
                    if (drop.hasUrls && drop.urls.length > 0) {
                        for (var i = 0; i < drop.urls.length; i++)
                            linuxcue.importProfile(drop.urls[i])
                    }
                    drop.acceptProposedAction()
                }
            }

            Rectangle {
                anchors.fill: parent
                visible: profileDropArea.containsDrag
                z: 20
                color: "#8012e8ff"
                border.color: "#d7ff37"
                border.width: 2
                Text {
                    anchors.centerIn: parent
                    width: parent.width - 48
                    text: "Profil hier ablegen\\n.json oder .cueprofile"
                    color: "white"
                    horizontalAlignment: Text.AlignHCenter
                    font.pixelSize: 18
                    font.bold: true
                }
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 18
                spacing: 18

                RowLayout {
                    spacing: 12
                    Rectangle {
                        width: 58
                        height: 58
                        radius: 16
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "#10d8f5" }
                            GradientStop { position: 0.58; color: "#145a66" }
                            GradientStop { position: 1.0; color: "#d7ff37" }
                        }
                        Text {
                            anchors.centerIn: parent
                            text: "lc"
                            color: "#081014"
                            font.bold: true
                            font.pixelSize: 18
                        }
                    }
                    ColumnLayout {
                        spacing: 0
                        Text { text: "linuxcue"; color: "white"; font.pixelSize: 31; font.bold: true }
                        Text { text: "Corsair control for Linux"; color: "#9db3bb"; font.pixelSize: 13 }
                    }
                }

                Text {
                    text: "PROFILES"
                    color: "#a8b8c0"
                    font.pixelSize: 12
                    font.bold: true
                }

                ListView {
                    id: profileList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: linuxcue.profiles
                    spacing: 8
                    MouseArea {
                        anchors.fill: parent
                        acceptedButtons: Qt.RightButton
                        propagateComposedEvents: true
                        onClicked: function(mouse) {
                            if (mouse.button === Qt.RightButton)
                                profileAreaMenu.popup()
                            mouse.accepted = false
                        }
                    }
                    delegate: Rectangle {
                        width: profileList.width
                        height: 72
                        radius: 12
                        color: modelData.selected ? "#12535f" : "transparent"
                        border.color: modelData.selected ? "#12e8ff" : "transparent"
                        Rectangle {
                            width: modelData.selected ? 4 : 0
                            height: parent.height - 14
                            y: 7
                            radius: 2
                            color: "#12e8ff"
                        }
                        Column {
                            anchors.left: parent.left
                            anchors.leftMargin: 18
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 3
                            Text { text: modelData.name; color: "white"; font.pixelSize: 15 }
                            Text { text: modelData.subtitle; color: "#c6d8de"; font.pixelSize: 12 }
                        }
                        MouseArea {
                            anchors.fill: parent
                            acceptedButtons: Qt.LeftButton | Qt.RightButton
                            onClicked: function(mouse) {
                                if (mouse.button === Qt.LeftButton) {
                                    resetDeviceViews()
                                    linuxcue.selectProfile(modelData.name)
                                    if (autoLiveWrite)
                                        profileLiveWriteTimer.restart()
                                } else {
                                    contextProfileName = modelData.name
                                    contextProfileProtected = Boolean(modelData.protected)
                                    profileItemMenu.popup()
                                }
                            }
                        }
                    }
                }

                Menu {
                    id: profileAreaMenu
                    MenuItem { text: "Neues Profil"; onTriggered: linuxcue.createProfileSet("Neues Profil") }
                    MenuSeparator {}
                    MenuItem { text: "Kopiertes Profil einfuegen"; onTriggered: linuxcue.pasteProfile() }
                }

                Menu {
                    id: profileItemMenu
                    MenuItem { text: "Profil kopieren"; onTriggered: linuxcue.copyProfile(contextProfileName) }
                    MenuItem { text: "Kopie erstellen"; onTriggered: linuxcue.duplicateProfile(contextProfileName) }
                    MenuItem { text: "Profil exportieren"; onTriggered: exportDialog.open() }
                    MenuSeparator {}
                    MenuItem {
                        text: contextProfileProtected ? "Standardprofil ist geschuetzt" : "Profil loeschen"
                        enabled: !contextProfileProtected
                        onTriggered: deleteConfirm.open()
                    }
                }

                Dialog {
                    id: deleteConfirm
                    title: "Profil loeschen"
                    modal: true
                    standardButtons: Dialog.Yes | Dialog.No
                    Text {
                        text: "Profil '" + contextProfileName + "' wirklich loeschen?"
                        color: "white"
                    }
                    onAccepted: linuxcue.deleteProfile(contextProfileName)
                }

                FileDialog {
                    id: importDialog
                    title: "Profil importieren"
                    nameFilters: ["linuxcue/iCUE Profile (*.json *.cueprofile)", "Alle Dateien (*)"]
                    onAccepted: linuxcue.importProfile(selectedFile.toString())
                }

                FileDialog {
                    id: exportDialog
                    title: "Profil exportieren"
                    fileMode: FileDialog.SaveFile
                    nameFilters: ["linuxcue JSON Profile (*.json)", "linuxcue cueprofile Bundle (*.cueprofile)"]
                    currentFile: contextProfileName + ".json"
                    onAccepted: linuxcue.exportProfile(contextProfileName, selectedFile.toString())
                }

                Menu {
                    id: layerMenu
                    MenuItem { text: "Kopieren"; onTriggered: linuxcue.copyLightingLayer(contextLayerId) }
                    MenuItem {
                        text: "Umbenennen"
                        onTriggered: {
                            renameLayerField.text = contextLayerTitle
                            renameLayerDialog.open()
                        }
                    }
                    MenuSeparator {}
                    MenuItem { text: "Loeschen"; onTriggered: linuxcue.deleteLightingLayer(contextLayerId) }
                }

                Menu {
                    id: m65DpiPresetMenu
                    MenuItem {
                        text: contextM65DpiPresetDefault ? "Default kann nicht geloescht werden" : "DPI-Gruppe loeschen"
                        enabled: !contextM65DpiPresetDefault
                        onTriggered: linuxcue.deleteM65DpiPreset(contextM65DpiPresetId)
                    }
                }

                Menu {
                    id: selectionMenu
                    MenuItem { text: "Auswahl kopieren"; onTriggered: copiedSelectionTarget = k95SelectedQuickZone }
                    MenuItem {
                        text: "Zur aktiven Schicht hinzufuegen"
                        enabled: k95HasSelection
                        onTriggered: {
                            linuxcue.addK95SelectionToLayer(k95SelectedQuickZone, autoLiveWrite)
                            exitK95LayerEdit()
                        }
                    }
                    MenuItem {
                        text: "Aus aktiver Schicht entfernen"
                        enabled: k95HasSelection
                        onTriggered: {
                            linuxcue.removeK95SelectionFromLayer(k95SelectedQuickZone, autoLiveWrite)
                            exitK95LayerEdit()
                        }
                    }
                    MenuSeparator {}
                    MenuItem {
                        text: "Auswahl loeschen"
                        onTriggered: {
                            exitK95LayerEdit()
                        }
                    }
                }

                Dialog {
                    id: renameLayerDialog
                    title: "Beleuchtungsschicht umbenennen"
                    modal: true
                    standardButtons: Dialog.Ok | Dialog.Cancel
                    width: 320
                    contentItem: TextField {
                        id: renameLayerField
                        selectByMouse: true
                        placeholderText: "Name"
                    }
                    onAccepted: linuxcue.renameLightingLayer(contextLayerId, renameLayerField.text)
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 82
                    radius: 14
                    color: "#10231d"
                    border.color: "#264438"
                    Text {
                        anchors.fill: parent
                        anchors.margins: 14
                        text: "Profil anklicken: Auswahl wirkt direkt auf die verbundene Hardware."
                        wrapMode: Text.WordWrap
                        color: "#a8c9c2"
                        font.pixelSize: 13
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Button { Layout.fillWidth: true; text: "Import"; onClicked: importDialog.open() }
                    Button {
                        Layout.fillWidth: true
                        text: "Export"
                        onClicked: {
                            contextProfileName = linuxcue.currentProfile
                            exportDialog.open()
                        }
                    }
                    Button { Layout.fillWidth: true; text: "Refresh"; onClicked: linuxcue.refresh() }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Button { Layout.fillWidth: true; text: "Update pruefen"; onClicked: linuxcue.checkForUpdates() }
                    Button {
                        id: installUpdateButton
                        Layout.fillWidth: true
                        text: linuxcue.updateAvailable ? "Update installieren" : "Kein Update"
                        enabled: linuxcue.updateAvailable
                        scale: 1.0
                        onClicked: linuxcue.installUpdate()
                        SequentialAnimation on scale {
                            running: linuxcue.updateAvailable
                            loops: Animation.Infinite
                            NumberAnimation { to: 1.025; duration: 520; easing.type: Easing.InOutQuad }
                            NumberAnimation { to: 1.0; duration: 520; easing.type: Easing.InOutQuad }
                        }
                        background: Rectangle {
                            radius: 7
                            color: linuxcue.updateAvailable ? "#d6ff28" : "#1f292d"
                            border.width: linuxcue.updateAvailable ? 2 : 1
                            border.color: linuxcue.updateAvailable ? "#f5ff00" : "#31444a"
                        }
                        contentItem: Text {
                            text: installUpdateButton.text
                            color: linuxcue.updateAvailable ? "#061010" : "#8fa4a8"
                            font.bold: linuxcue.updateAvailable
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                }

                Text {
                    Layout.fillWidth: true
                    text: linuxcue.status
                    color: "#a9c8c8"
                    wrapMode: Text.WordWrap
                    font.pixelSize: 12
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: 16
            spacing: 12

            RowLayout {
                Layout.fillWidth: true
                height: 92
                spacing: 10

                Repeater {
                    model: linuxcue.devices
                    delegate: DeviceCard {
                        Layout.preferredWidth: 130
                        Layout.preferredHeight: 78
                        title: modelData.title
                        kind: modelData.kind
                        meta: modelData.meta
                        state: modelData.state
                        selected: modelData.slug === linuxcue.currentDevice
                        slug: modelData.slug
                        imageSource: modelData.imageSource === undefined ? "" : modelData.imageSource
                        wireless: modelData.wireless === true
                        onClicked: linuxcue.selectDevice(modelData.slug)
                    }
                }

                Item { Layout.fillWidth: true }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 18
                color: "transparent"
                visible: showK95Dashboard

                RowLayout {
                    anchors.fill: parent
                    spacing: 14

                    ColumnLayout {
                        Layout.preferredWidth: 206
                        Layout.maximumWidth: 206
                        Layout.minimumWidth: 206
                        Layout.fillHeight: true
                        spacing: 10

                        Panel {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 196
                            title: "K95 RGB PLATINUM"
                            Item {
                                anchors.fill: parent
                                anchors.margins: 10
                                anchors.topMargin: 40
                                clip: true
                                ToggleLine {
                                    width: parent.width
                                    y: 0
                                    text: "Geraetespeichermodus"
                                }
                                NavLine {
                                    width: parent.width
                                    y: 34
                                    text: "Beleuchtungseffekte"
                                    selected: k95Section === "lighting"
                                    onClicked: k95Section = "lighting"
                                }
                                NavLine {
                                    width: parent.width
                                    y: 68
                                    text: "Tastenzuweisungen"
                                    selected: k95Section === "keys"
                                    onClicked: k95Section = "keys"
                                }
                                NavLine {
                                    width: parent.width
                                    y: 96
                                    text: "Optionen"
                                    selected: k95Section === "options"
                                    onClicked: {
                                        clearK95Selection()
                                        k95Section = "options"
                                    }
                                }
                            }
                        }

                        Panel {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            title: "Beleuchtungsschichten"
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 12
                                anchors.topMargin: 44
                                spacing: 7
                                Button {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 28
                                    text: "+"
                                    font.pixelSize: 20
                                    font.bold: false
                                    onClicked: {
                                        linuxcue.addLightingLayer("Statische Farbe")
                                        clearK95Selection()
                                        k95KeyboardPreview.clearSelection()
                                    }
                                    contentItem: Text {
                                        text: parent.text
                                        color: "#050808"
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                        font.pixelSize: 20
                                    }
                                    background: Rectangle {
                                        radius: 4
                                        color: "#f2eb00"
                                    }
                                }
                                Repeater {
                                    model: linuxcue.lightingLayers
                                    delegate: LightingLayer {
                                        layerId: modelData.id
                                        title: modelData.title
                                        colorValue: modelData.color
                                        selected: modelData.selected
                                        onClicked: function(layerId) {
                                            if (k95EditingLayerId === layerId) {
                                                exitK95LayerEdit()
                                                return
                                            }
                                            linuxcue.selectLightingLayer(layerId)
                                            k95EditingLayerId = layerId
                                            selectedColor = modelData.color
                                            k95SelectedQuickZone = modelData.zone
                                            k95SelectedKeys = modelData.keys
                                            k95SelectedKey = modelData.keys.length === 1 ? modelData.keys[0] : ""
                                            k95HasSelection = modelData.keys.length > 0
                                            showK95EffectPicker = modelData.keys.length > 0
                                            k95SelectedEffect = modelData.keys.length > 0 ? "Statische Farbe" : ""
                                            k95KeyboardPreview.setSelection(modelData.keys, false)
                                        }
                                        onRightClicked: function(layerId, title) {
                                            contextLayerId = layerId
                                            contextLayerTitle = title
                                            layerMenu.popup()
                                        }
                                    }
                                }
                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 28
                                    visible: k95HasSelection && showK95EffectPicker && k95SelectedEffect === "Statische Farbe"
                                    radius: 4
                                    color: "#d9d9d9"
                                    Text {
                                        anchors.verticalCenter: parent.verticalCenter
                                        anchors.left: parent.left
                                        anchors.leftMargin: 10
                                        text: k95SelectedKeys.length > 1 ? "Tasten: " + k95SelectedKeys.length : (k95SelectedKey !== "" ? "Taste: " + k95SelectedKey.toUpperCase() : "Zone: " + zoneTitle(k95SelectedQuickZone))
                                        color: "#101417"
                                        font.pixelSize: 12
                                        font.bold: true
                                        elide: Text.ElideRight
                                        width: parent.width - 20
                                    }
                                    MouseArea {
                                        anchors.fill: parent
                                        acceptedButtons: Qt.RightButton
                                        onClicked: function(mouse) {
                                            if (mouse.button === Qt.RightButton)
                                                selectionMenu.popup()
                                        }
                                    }
                                }
                                Item { Layout.fillHeight: true }
                                Text { text: "Beleuchtungsbibliothek  >"; color: "#8f9da3"; font.pixelSize: 12 }
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 14

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: Math.min(470, Math.max(370, window.height * 0.44))
                            Layout.minimumHeight: 360
                            radius: 20
                            color: "#171a1a"
                            border.color: "#24343a"
                            border.width: 1
                            visible: k95Section === "lighting"

                            Rectangle {
                                anchors.fill: parent
                                anchors.margins: 1
                                radius: 19
                                opacity: 0.78
                                gradient: Gradient {
                                    GradientStop { position: 0.0; color: "#232829" }
                                    GradientStop { position: 0.45; color: "#1b1e1f" }
                                    GradientStop { position: 1.0; color: "#111314" }
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                acceptedButtons: Qt.LeftButton
                                onClicked: {}
                            }

                            Text {
                                anchors.left: parent.left
                                anchors.top: parent.top
                                anchors.leftMargin: 26
                                anchors.topMargin: 20
                                text: "K95 RGB Platinum"
                                color: "#ffffff"
                                font.bold: true
                                font.pixelSize: 21
                            }

                            Text {
                                anchors.left: parent.left
                                anchors.top: parent.top
                                anchors.leftMargin: 26
                                anchors.topMargin: 50
                                text: "Beleuchtungseffekte: per Taste, Auswahlrahmen oder Schnellzone"
                                color: "#91aeb2"
                                font.pixelSize: 13
                            }

                            Rectangle {
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.rightMargin: 24
                                anchors.topMargin: 22
                                width: 170
                                height: 34
                                radius: 17
                                color: "#d6ff28"
                                Text {
                                    anchors.centerIn: parent
                                    text: "ISO / DE layout map"
                                    color: "#061010"
                                    font.bold: true
                                    font.pixelSize: 12
                                }
                            }

                            KeyboardPreview {
                                id: k95KeyboardPreview
                                z: 2
                                anchors.horizontalCenter: parent.horizontalCenter
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.verticalCenterOffset: 34
                                width: Math.min(parent.width - 36, 1260)
                                height: Math.min(parent.height - 72, 390)
                                accentColor: selectedColor
                                keyColors: linuxcue.k95KeyColors
                                selectedKey: k95SelectedKey
                                selectedKeys: k95SelectedKeys
                                mergeDragSelection: k95EditingLayerId !== ""
                                onSelectionChanged: function(keys) {
                                    if (k95EditingLayerId !== "" && keys.length === 0) {
                                        k95KeyboardPreview.setSelection(k95SelectedKeys, false)
                                        return
                                    }
                                    k95SelectedKeys = keys
                                    k95SelectedKey = keys.length === 1 ? keys[0] : ""
                                    k95SelectedQuickZone = keys.length === 0 ? "all" : (keys.length === 1 ? "key:" + keys[0] : "keys:" + keys.join(","))
                                    k95HasSelection = keys.length > 0
                                    showK95EffectPicker = keys.length > 0
                                    k95SelectedEffect = keys.length > 0 ? "Statische Farbe" : ""
                                    if (k95EditingLayerId !== "" && keys.length > 0)
                                        linuxcue.setK95LightingLayerKeys(k95EditingLayerId, k95SelectedQuickZone, autoLiveWrite)
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Layout.preferredHeight: showK95EffectPicker ? 286 : 0
                            Layout.maximumHeight: showK95EffectPicker ? 300 : 0
                            visible: k95Section === "lighting" && showK95EffectPicker
                            spacing: 12

                            Panel {
                                Layout.preferredWidth: 250
                                Layout.fillHeight: true
                                title: "Beleuchtungstyp"
                                visible: showK95EffectPicker
                                EffectGrid {
                                    anchors.fill: parent
                                    anchors.margins: 14
                                    anchors.topMargin: 52
                                    selectedEffect: k95SelectedEffect
                                    onEffectPicked: function(effect) {
                                        k95SelectedEffect = effect
                                    }
                                }
                            }

                            Panel {
                                Layout.preferredWidth: 230
                                Layout.fillHeight: true
                                title: "Schnellbeleuchtungszone"
                                visible: showK95EffectPicker && k95SelectedEffect === "Statische Farbe"
                                QuickZones {
                                    anchors.fill: parent
                                    anchors.margins: 14
                                    anchors.topMargin: 52
                                    selectedZone: k95SelectedQuickZone
                                    onZonePicked: function(zone) {
                                        k95SelectedQuickZone = zone
                                        k95SelectedKey = ""
                                        k95SelectedKeys = []
                                        k95HasSelection = true
                                    }
                                }
                            }

                            Panel {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                title: "Statische Farbe"
                                visible: showK95EffectPicker && k95SelectedEffect === "Statische Farbe"
                                ColorPanel {
                                    anchors.fill: parent
                                    anchors.margins: 18
                                    anchors.topMargin: 58
                                    currentColor: selectedColor
                                    onColorPicked: {
                                        selectedColor = color
                                        if (k95EditingLayerId !== "")
                                            linuxcue.setK95LightingLayerColor(k95EditingLayerId, color, autoLiveWrite)
                                        else
                                            linuxcue.applyK95ColorToZone(k95SelectedQuickZone, color, autoLiveWrite)
                                    }
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            visible: k95Section === "options"
                            spacing: 14

                            Panel {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                title: "Optionen"
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 18
                                    anchors.topMargin: 58
                                    spacing: 14
                                    Text {
                                        text: "Wenn WIN-LOCK aktiviert ist:"
                                        color: "#ffffff"
                                        font.pixelSize: 14
                                        font.bold: true
                                    }
                                    ToggleLine { Layout.fillWidth: true; text: "Alt+Tab deaktivieren"; onToggled: function(checked) { linuxcue.setK95Option("disable_alt_tab", checked, autoLiveWrite) } }
                                    ToggleLine { Layout.fillWidth: true; text: "Alt+F4 deaktivieren"; onToggled: function(checked) { linuxcue.setK95Option("disable_alt_f4", checked, autoLiveWrite) } }
                                    ToggleLine { Layout.fillWidth: true; text: "Umschalt+Tab deaktivieren"; onToggled: function(checked) { linuxcue.setK95Option("disable_shift_tab", checked, autoLiveWrite) } }
                                    ToggleLine { Layout.fillWidth: true; text: "WINDOWS-TASTE deaktivieren"; checked: true; onToggled: function(checked) { linuxcue.setK95Option("disable_windows_key", checked, autoLiveWrite) } }
                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 58
                                        radius: 10
                                        color: "#2b2208"
                                        border.color: "#8a6f19"
                                        Text {
                                            anchors.fill: parent
                                            anchors.margins: 12
                                            text: "Hinweis: Die bekannten K95-Setup-Pakete koennen gesendet werden. Einige Win-Lock-Sperr-Bits brauchen noch Capture-Daten."
                                            color: "#ffd66b"
                                            wrapMode: Text.WordWrap
                                            font.pixelSize: 12
                                        }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Button { text: "Options Sync"; onClicked: linuxcue.k95OptionsSync() }
                                        Button { text: "Hardware Mode"; onClicked: linuxcue.k95HardwareMode() }
                                        Button {
                                            text: "Standard"
                                            onClicked: {
                                                linuxcue.applyK95ColorToZone("key:lock", "#1ecfdf", autoLiveWrite)
                                                linuxcue.applyK95ColorToZone("key:brightness", "#ffffff", autoLiveWrite)
                                                linuxcue.applyK95ColorToZone("key:preset", "#ff001f", autoLiveWrite)
                                            }
                                        }
                                    }
                                    Item { Layout.fillHeight: true }
                                }
                            }

                            Panel {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                title: "Anzeigefarben"
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 18
                                    anchors.topMargin: 58
                                    spacing: 16
                                    Text { text: "Sperren"; color: "#ffffff"; font.bold: true; font.pixelSize: 14 }
                                    RowLayout {
                                        spacing: 18
                                        OptionColorButton { label: "Ein"; colorValue: "#1ecfdf"; onPicked: linuxcue.applyK95ColorToZone("key:lock", "#1ecfdf", autoLiveWrite) }
                                        OptionColorButton { label: "Aus"; colorValue: "#ff001f"; onPicked: linuxcue.applyK95ColorToZone("key:lock", "#ff001f", autoLiveWrite) }
                                    }
                                    Text { text: "Helligkeit"; color: "#ffffff"; font.bold: true; font.pixelSize: 14 }
                                    OptionColorButton { label: "Taste"; colorValue: "#ffffff"; onPicked: linuxcue.applyK95ColorToZone("key:brightness", "#ffffff", autoLiveWrite) }
                                    Text { text: "Profil"; color: "#ffffff"; font.bold: true; font.pixelSize: 14 }
                                    OptionColorButton { label: "Taste"; colorValue: "#ff001f"; onPicked: linuxcue.applyK95ColorToZone("key:preset", "#ff001f", autoLiveWrite) }
                                    Item { Layout.fillHeight: true }
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 18
                color: "transparent"
                visible: showM65Dashboard

                RowLayout {
                    anchors.fill: parent
                    spacing: 14

                    ColumnLayout {
                        Layout.preferredWidth: 260
                        Layout.maximumWidth: 260
                        Layout.minimumWidth: 260
                        Layout.fillHeight: true
                        spacing: 10

                        Panel {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 300
                            title: "M65 PRO RGB"
                            Item {
                                anchors.fill: parent
                                anchors.margins: 12
                                anchors.topMargin: 58
                                clip: true
                                ToggleLine {
                                    width: parent.width
                                    y: 0
                                    text: "Geraetespeichermodus"
                                }
                                Rectangle {
                                    width: parent.width - 8
                                    height: 1
                                    y: 34
                                    x: 4
                                    color: "#2b3235"
                                }
                                NavLine {
                                    width: parent.width
                                    y: 58
                                    text: "Beleuchtungseffekte"
                                    selected: m65Section === "lighting"
                                    onClicked: m65Section = "lighting"
                                }
                                NavLine {
                                    width: parent.width
                                    y: 96
                                    text: "Tastenzuweisungen"
                                    selected: m65Section === "buttons"
                                    onClicked: m65Section = "buttons"
                                }
                                NavLine {
                                    width: parent.width
                                    y: 134
                                    text: "DPI"
                                    selected: m65Section === "dpi"
                                    onClicked: m65Section = "dpi"
                                }
                                NavLine {
                                    width: parent.width
                                    y: 172
                                    text: "Oberflaechenkalibrierung"
                                    selected: m65Section === "calibration"
                                    onClicked: m65Section = "calibration"
                                }
                            }
                        }

                        Panel {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            title: m65Section === "dpi" ? "DPI-Voreinstellungen" : (m65Section === "lighting" ? "Beleuchtungsschichten" : "Hinweis")
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 14
                                anchors.topMargin: 46
                                spacing: 8

                                Button {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 30
                                    text: "+"
                                    visible: m65Section === "lighting" || m65Section === "dpi"
                                    onClicked: {
                                        if (m65Section === "dpi")
                                            linuxcue.createM65DpiPreset()
                                    }
                                    background: Rectangle { radius: 5; color: "#f2eb00" }
                                    contentItem: Text {
                                        text: parent.text
                                        color: "#050808"
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                        font.pixelSize: 20
                                    }
                                }

                                Repeater {
                                    model: m65Section === "dpi" ? linuxcue.m65DpiPresets : (m65Section === "lighting" ? linuxcue.m65LightingZones : [])
                                    delegate: Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 32
                                        radius: 5
                                        color: {
                                            if (m65Section === "dpi")
                                                return modelData.active ? "#565656" : "transparent"
                                            return modelData.name === m65SelectedZone ? "#565656" : "transparent"
                                        }
                                        border.color: "transparent"
                                        Rectangle {
                                            width: 18
                                            height: 18
                                            radius: 4
                                            color: m65Section === "dpi" ? "#2b3033" : modelData.color
                                            visible: m65Section !== "dpi"
                                            anchors.left: parent.left
                                            anchors.leftMargin: 8
                                            anchors.verticalCenter: parent.verticalCenter
                                        }
                                        Text {
                                            text: m65Section === "dpi" ? modelData.name : modelData.title
                                            color: "white"
                                            font.pixelSize: 13
                                            anchors.left: parent.left
                                            anchors.leftMargin: m65Section === "dpi" ? 12 : 36
                                            anchors.verticalCenter: parent.verticalCenter
                                            width: parent.width - (m65Section === "dpi" ? 58 : 48)
                                            elide: Text.ElideRight
                                        }
                                        Text {
                                            visible: m65Section === "dpi"
                                            text: modelData.isDefault ? "⌂" : "⋮"
                                            color: modelData.isDefault ? "#d6ff28" : "#a6b3b7"
                                            font.pixelSize: modelData.isDefault ? 14 : 18
                                            anchors.right: parent.right
                                            anchors.rightMargin: 12
                                            anchors.verticalCenter: parent.verticalCenter
                                        }
                                        MouseArea {
                                            anchors.fill: parent
                                            acceptedButtons: Qt.LeftButton | Qt.RightButton
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: function(mouse) {
                                                if (m65Section === "dpi" && mouse.button === Qt.RightButton) {
                                                    contextM65DpiPresetId = modelData.id
                                                    contextM65DpiPresetName = modelData.name
                                                    contextM65DpiPresetDefault = modelData.isDefault
                                                    m65DpiPresetMenu.popup()
                                                } else if (m65Section === "dpi") {
                                                    linuxcue.selectM65DpiPreset(modelData.id)
                                                } else {
                                                    m65SelectedZone = modelData.name
                                                    m65SelectedColor = modelData.color
                                                }
                                            }
                                        }
                                    }
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 86
                                    radius: 10
                                    color: "#07130f"
                                    border.color: "#264438"
                                    visible: m65Section === "buttons" || m65Section === "calibration"
                                    Text {
                                        anchors.fill: parent
                                        anchors.margins: 12
                                        text: m65Section === "buttons"
                                              ? "Die nativen DPI-Tasten laufen ueber die Hardware. Freie Tastenzuweisungen bleiben sichtbar, bis wir sichere HID-Pakete dafuer haben."
                                              : "Oberflaechenkalibrierung ist als eigener Bereich angelegt. Fuer echte Kalibrierung brauchen wir spaeter passende Capture-Daten."
                                        color: "#a8c9c2"
                                        wrapMode: Text.WordWrap
                                        font.pixelSize: 12
                                    }
                                }
                                Item { Layout.fillHeight: true }
                                Text {
                                    text: m65Section === "dpi" ? "DPI-Speicher  >" : "Beleuchtungsbibliothek  >"
                                    visible: m65Section === "lighting" || m65Section === "dpi"
                                    color: "#8f9da3"
                                    font.pixelSize: 12
                                }
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 12

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: Math.min(360, Math.max(270, window.height * 0.34))
                            radius: 20
                            color: "#1d2020"
                            border.color: "#24343a"
                            clip: true
                            Rectangle {
                                anchors.fill: parent
                                anchors.margins: 1
                                radius: 19
                                gradient: Gradient {
                                    GradientStop { position: 0.0; color: "#232829" }
                                    GradientStop { position: 0.55; color: "#1b1e1f" }
                                    GradientStop { position: 1.0; color: "#111314" }
                                }
                            }
                            Text {
                                anchors.left: parent.left
                                anchors.top: parent.top
                                anchors.leftMargin: 26
                                anchors.topMargin: 22
                                text: "M65 Pro RGB"
                                color: "white"
                                font.bold: true
                                font.pixelSize: 22
                            }
                            Text {
                                anchors.left: parent.left
                                anchors.top: parent.top
                                anchors.leftMargin: 26
                                anchors.topMargin: 54
                                text: m65Section === "dpi" ? "DPI-Stufen werden im Geraeteprofil gesetzt" : "Beleuchtung: Logo, Vorderseite und DPI-Indikator"
                                color: "#91aeb2"
                                font.pixelSize: 13
                            }
                            Rectangle {
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.rightMargin: 24
                                anchors.topMargin: 22
                                width: 154
                                height: 34
                                radius: 17
                                color: "#d6ff28"
                                Text {
                                    anchors.centerIn: parent
                                    text: "DPI + RGB mapped"
                                    color: "#061010"
                                    font.bold: true
                                    font.pixelSize: 12
                                }
                            }
                            Rectangle {
                                id: m65HeroImageWell
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.horizontalCenter: parent.horizontalCenter
                                anchors.horizontalCenterOffset: parent.width * 0.06
                                width: Math.min(500, parent.width * 0.40)
                                height: parent.height - 64
                                radius: 20
                                clip: true
                                color: "transparent"
                                border.color: "transparent"
                                opacity: 1.0

                                Rectangle {
                                    anchors.fill: parent
                                    radius: parent.radius
                                    color: "#0c1314"
                                    opacity: 0.03
                                }
                                Rectangle {
                                    anchors.centerIn: parent
                                    width: parent.width * 0.86
                                    height: parent.height * 0.94
                                    radius: height / 2
                                    gradient: Gradient {
                                        GradientStop { position: 0.0; color: "#153426" }
                                        GradientStop { position: 0.55; color: "#102521" }
                                        GradientStop { position: 1.0; color: "#071012" }
                                    }
                                    opacity: 0.10
                                }
                                Image {
                                    anchors.centerIn: parent
                                    anchors.horizontalCenterOffset: -14
                                    width: parent.width * 0.98
                                    height: parent.height * 0.94
                                    source: "../assets/devices/m65-preview-cutout.png"
                                    fillMode: Image.PreserveAspectFit
                                    smooth: true
                                    mipmap: true
                                    opacity: 0.98
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            visible: m65Section === "lighting"
                            spacing: 12

                            Panel {
                                Layout.preferredWidth: 260
                                Layout.fillHeight: true
                                title: "Beleuchtungstyp"
                                EffectGrid {
                                    anchors.fill: parent
                                    anchors.margins: 14
                                    anchors.topMargin: 52
                                    selectedEffect: "Statische Farbe"
                                }
                            }

                            Panel {
                                Layout.preferredWidth: 230
                                Layout.fillHeight: true
                                title: "Schnellbeleuchtungszone"
                                Grid {
                                    anchors.fill: parent
                                    anchors.margins: 14
                                    anchors.topMargin: 58
                                    columns: 2
                                    spacing: 10
                                    Repeater {
                                        model: [
                                            { "zone": "all", "label": "Alle" },
                                            { "zone": "front", "label": "Vorderseite" },
                                            { "zone": "logo", "label": "Logo" },
                                            { "zone": "dpi_indicator", "label": "DPI" }
                                        ]
                                        delegate: Button {
                                            width: 96
                                            height: 42
                                            text: modelData.label
                                            highlighted: m65SelectedZone === modelData.zone
                                            onClicked: {
                                                m65SelectedZone = modelData.zone
                                                m65SelectedColor = m65ZoneColor(modelData.zone)
                                            }
                                        }
                                    }
                                }
                            }

                            Panel {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                title: "Statische Farbe"
                                ColorPanel {
                                    anchors.fill: parent
                                    anchors.margins: 18
                                    anchors.topMargin: 58
                                    currentColor: m65ZoneColor(m65SelectedZone)
                                    onColorPicked: {
                                        m65SelectedColor = color
                                        linuxcue.applyM65ColorToZone(m65SelectedZone, color, autoLiveWrite)
                                    }
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            visible: m65Section === "dpi"
                            spacing: 12

                            Panel {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                title: "DPI-Stufen"
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 18
                                    anchors.topMargin: 56
                                    spacing: 9
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 34
                                        Item { Layout.fillWidth: true }
                                        Button {
                                            Layout.preferredWidth: 230
                                            Layout.preferredHeight: 32
                                            text: "Defaultwerte wiederherstellen"
                                            onClicked: linuxcue.resetM65DpiPreset()
                                            background: Rectangle {
                                                radius: 7
                                                color: "#202c31"
                                                border.color: "#39545d"
                                            }
                                            contentItem: Text {
                                                text: parent.text
                                                color: "white"
                                                font.bold: true
                                                horizontalAlignment: Text.AlignHCenter
                                                verticalAlignment: Text.AlignVCenter
                                            }
                                        }
                                    }
                                    Repeater {
                                        model: linuxcue.m65DpiStages
                                        delegate: RowLayout {
                                            Layout.fillWidth: true
                                            spacing: 12
                                            RadioButton {
                                                checked: modelData.active
                                                onClicked: linuxcue.setM65ActiveDpiStage(modelData.index, autoLiveWrite)
                                            }
                                            Text {
                                                Layout.preferredWidth: 86
                                                text: modelData.title
                                                color: "white"
                                                font.bold: modelData.active
                                            }
                                            Slider {
                                                id: dpiSlider
                                                Layout.fillWidth: true
                                                from: 100
                                                to: 18000
                                                stepSize: 100
                                                value: modelData.x
                                                onPressedChanged: {
                                                    if (!pressed)
                                                        linuxcue.setM65DpiStage(modelData.index, Math.round(value / 100) * 100, Math.round(yDpi.value / 100) * 100, autoLiveWrite)
                                                }
                                            }
                                            SpinBox {
                                                id: xDpi
                                                Layout.preferredWidth: 116
                                                from: 100
                                                to: 18000
                                                stepSize: 100
                                                value: modelData.x
                                                editable: true
                                                textFromValue: function(value, locale) { return value.toString() }
                                                valueFromText: function(text, locale) { return Number(text.replace(".", "")) }
                                                onValueModified: linuxcue.setM65DpiStage(modelData.index, value, yDpi.value, false)
                                            }
                                            Text { text: "X"; color: "#9fb6bb" }
                                            SpinBox {
                                                id: yDpi
                                                Layout.preferredWidth: 116
                                                from: 100
                                                to: 18000
                                                stepSize: 100
                                                value: modelData.y
                                                editable: true
                                                textFromValue: function(value, locale) { return value.toString() }
                                                valueFromText: function(text, locale) { return Number(text.replace(".", "")) }
                                                onValueModified: linuxcue.setM65DpiStage(modelData.index, xDpi.value, value, false)
                                            }
                                            Text { text: "Y"; color: "#9fb6bb" }
                                            Rectangle {
                                                width: 16
                                                height: 16
                                                radius: 8
                                                color: modelData.color
                                                border.color: "white"
                                                border.width: modelData.active ? 2 : 0
                                            }
                                        }
                                    }
                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 58
                                        radius: 10
                                        color: "#2b2208"
                                        border.color: "#8a6f19"
                                        Text {
                                            anchors.fill: parent
                                            anchors.margins: 12
                                            text: "DPI-Live-Write setzt aktuell den aktiven Hardware-Slot. Die numerischen DPI-Werte bleiben im Profil sichtbar und werden fuer die naechsten HID-Erweiterungen behalten."
                                            color: "#ffd66b"
                                            wrapMode: Text.WordWrap
                                            font.pixelSize: 12
                                        }
                                    }
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 16
                            color: "#0d1113"
                            border.color: "#24363d"
                            visible: m65Section === "buttons" || m65Section === "calibration"
                            Text {
                                anchors.centerIn: parent
                                width: parent.width - 80
                                text: m65Section === "buttons"
                                      ? "Tastenzuweisungen sind als Profilbereich vorbereitet. Die Hauptfunktionen der DPI-Tasten laufen nativ ueber den M65-Hardwaremodus."
                                      : "Oberflaechenkalibrierung ist vorbereitet, aber noch ohne bestaetigte HID-Kommandos."
                                color: "#9fb6bb"
                                horizontalAlignment: Text.AlignHCenter
                                wrapMode: Text.WordWrap
                                font.pixelSize: 16
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 18
                color: "transparent"
                visible: showVirtuosoDashboard

                RowLayout {
                    anchors.fill: parent
                    spacing: 14

                    ColumnLayout {
                        Layout.preferredWidth: 260
                        Layout.maximumWidth: 260
                        Layout.minimumWidth: 260
                        Layout.fillHeight: true
                        spacing: 10

                        Panel {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 260
                            title: "VIRTUOSO SE"
                            Item {
                                anchors.fill: parent
                                anchors.margins: 12
                                anchors.topMargin: 58
                                clip: true
                                Rectangle {
                                    width: parent.width - 8
                                    height: 1
                                    y: 0
                                    x: 4
                                    color: "#2b3235"
                                }
                                NavLine {
                                    width: parent.width
                                    y: 24
                                    text: "Beleuchtungseffekte"
                                    selected: virtuosoSection === "lighting"
                                    onClicked: virtuosoSection = "lighting"
                                }
                                NavLine {
                                    width: parent.width
                                    y: 62
                                    text: "NVIDIA"
                                    selected: virtuosoSection === "nvidia"
                                    onClicked: virtuosoSection = "nvidia"
                                }
                                NavLine {
                                    width: parent.width
                                    y: 100
                                    text: "Equalizer"
                                    selected: virtuosoSection === "eq"
                                    onClicked: virtuosoSection = "eq"
                                }
                            }
                        }

                        Panel {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            title: virtuosoSection === "eq" ? "Audio Presets" : "Beleuchtungsschichten"
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 14
                                anchors.topMargin: 46
                                spacing: 8
                                Button {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 30
                                    text: "+"
                                    visible: virtuosoSection === "lighting"
                                    background: Rectangle { radius: 5; color: "#f2eb00" }
                                    contentItem: Text {
                                        text: parent.text
                                        color: "#050808"
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                        font.pixelSize: 20
                                    }
                                }
                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 30
                                    radius: 4
                                    color: "#565656"
                                    visible: virtuosoSection === "lighting"
                                    Rectangle {
                                        width: 18
                                        height: 18
                                        radius: 4
                                        color: linuxcue.virtuosoAccentColor
                                        anchors.left: parent.left
                                        anchors.leftMargin: 8
                                        anchors.verticalCenter: parent.verticalCenter
                                    }
                                    Text {
                                        text: "Statische Farbe"
                                        color: "white"
                                        font.pixelSize: 13
                                        anchors.left: parent.left
                                        anchors.leftMargin: 36
                                        anchors.verticalCenter: parent.verticalCenter
                                    }
                                }
                                Repeater {
                                    model: linuxcue.virtuosoPresets
                                    delegate: Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 34
                                        radius: 6
                                        visible: virtuosoSection === "eq"
                                        color: modelData.selected ? "#565656" : "transparent"
                                        border.color: modelData.selected ? "#12e8ff" : "transparent"
                                        Text {
                                            anchors.verticalCenter: parent.verticalCenter
                                            anchors.left: parent.left
                                            anchors.leftMargin: 12
                                            text: modelData.name
                                            color: "white"
                                            font.pixelSize: 13
                                        }
                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: linuxcue.selectVirtuosoPreset(modelData.name, autoLiveWrite)
                                        }
                                    }
                                }
                                Item { Layout.fillHeight: true }
                                Text {
                                    text: virtuosoSection === "eq" ? "EasyEffects / PipeWire  >" : "Beleuchtungsbibliothek  >"
                                    color: "#8f9da3"
                                    font.pixelSize: 12
                                }
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 12

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: virtuosoSection === "lighting" ? Math.min(390, Math.max(300, window.height * 0.38)) : Math.min(260, Math.max(220, window.height * 0.28))
                            radius: 20
                            color: "#1d2020"
                            border.color: "#24343a"
                            Rectangle {
                                anchors.fill: parent
                                anchors.margins: 1
                                radius: 19
                                gradient: Gradient {
                                    GradientStop { position: 0.0; color: "#232829" }
                                    GradientStop { position: 0.55; color: "#1b1e1f" }
                                    GradientStop { position: 1.0; color: "#111314" }
                                }
                            }
                            Text {
                                anchors.left: parent.left
                                anchors.top: parent.top
                                anchors.leftMargin: 26
                                anchors.topMargin: 20
                                text: "Virtuoso SE"
                                color: "white"
                                font.bold: true
                                font.pixelSize: 22
                            }
                            Text {
                                anchors.left: parent.left
                                anchors.top: parent.top
                                anchors.leftMargin: 26
                                anchors.topMargin: 52
                                text: virtuosoSection === "eq" ? "10 Band Equalizer wird ueber EasyEffects gesteuert" : "Beleuchtung: Logo/Accent-Ring als gespeicherte Profilfarbe"
                                color: "#91aeb2"
                                font.pixelSize: 13
                            }
                            Rectangle {
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.rightMargin: 24
                                anchors.topMargin: 22
                                width: 146
                                height: 34
                                radius: 17
                                color: "#d6ff28"
                                Text {
                                    anchors.centerIn: parent
                                    text: "EQ + RGB mapped"
                                    color: "#061010"
                                    font.bold: true
                                    font.pixelSize: 12
                                }
                            }
                            Rectangle {
                                id: virtuosoHeroImageFrame
                                anchors.horizontalCenter: parent.horizontalCenter
                                anchors.top: parent.top
                                anchors.topMargin: 62
                                anchors.horizontalCenterOffset: parent.width * 0.08
                                width: Math.min(320, parent.width * 0.34)
                                height: parent.height - 78
                                radius: 18
                                color: "transparent"
                                border.color: "transparent"
                                clip: false

                                Rectangle {
                                    anchors.centerIn: parent
                                    width: parent.width * 0.88
                                    height: parent.height * 0.78
                                    radius: width / 2
                                    color: "#15242a"
                                    opacity: 0.32
                                }

                                Image {
                                    anchors.centerIn: parent
                                    width: parent.width * 0.92
                                    height: parent.height * 0.94
                                    source: "../assets/devices/virtuoso-preview-cutout.png"
                                    fillMode: Image.PreserveAspectFit
                                    smooth: true
                                    mipmap: true
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            visible: virtuosoSection === "lighting"
                            spacing: 12

                            Panel {
                                Layout.preferredWidth: 260
                                Layout.fillHeight: true
                                title: "Beleuchtungstyp"
                                EffectGrid {
                                    anchors.fill: parent
                                    anchors.margins: 14
                                    anchors.topMargin: 52
                                    selectedEffect: "Statische Farbe"
                                }
                            }

                            Panel {
                                Layout.preferredWidth: 230
                                Layout.fillHeight: true
                                title: "Schnellbeleuchtungszone"
                                Column {
                                    anchors.fill: parent
                                    anchors.margins: 16
                                    anchors.topMargin: 58
                                    spacing: 14
                                    Button {
                                        width: 88
                                        height: 42
                                        text: "Logo"
                                        highlighted: true
                                    }
                                    Text {
                                        width: parent.width
                                        text: "Virtuoso nutzt aktuell die Accent-Ring/Logo-Zone aus dem Profil. Live-RGB ist weiterhin experimentell."
                                        color: "#8ea4aa"
                                        wrapMode: Text.WordWrap
                                        font.pixelSize: 12
                                    }
                                }
                            }

                            Panel {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                title: "Statische Farbe"
                                ColorPanel {
                                    anchors.fill: parent
                                    anchors.margins: 18
                                    anchors.topMargin: 58
                                    currentColor: linuxcue.virtuosoAccentColor
                                    onColorPicked: {
                                        selectedColor = color
                                        linuxcue.applyVirtuosoColor(color, autoLiveWrite)
                                    }
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            visible: virtuosoSection === "eq"
                            spacing: 12

                            Panel {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                title: "Equalizer"
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 18
                                    anchors.topMargin: 54
                                    spacing: 12
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Text { text: "EQ Preset"; color: "white"; font.bold: true; font.pixelSize: 14 }
                                        Item { Layout.fillWidth: true }
                                        ComboBox {
                                            id: virtuosoPresetBox
                                            Layout.preferredWidth: 190
                                            textRole: "name"
                                            model: linuxcue.virtuosoPresets
                                            currentIndex: activeVirtuosoPresetIndex()
                                            onActivated: function(index) {
                                                if (linuxcue.virtuosoPresets.length > index)
                                                    linuxcue.selectVirtuosoPreset(linuxcue.virtuosoPresets[index].name, autoLiveWrite)
                                            }
                                        }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        spacing: 22
                                        Repeater {
                                            model: linuxcue.virtuosoEqBands
                                            delegate: ColumnLayout {
                                                Layout.fillHeight: true
                                                spacing: 6
                                                property int liveBandIndex: index
                                                Text {
                                                    Layout.alignment: Qt.AlignHCenter
                                                    text: Math.round(eqSlider.value) >= 0 ? "+" + Math.round(eqSlider.value) : "" + Math.round(eqSlider.value)
                                                    color: "#d7ff28"
                                                    font.bold: true
                                                    font.pixelSize: 13
                                                }
                                                Timer {
                                                    id: eqSliderLiveTimer
                                                    interval: 280
                                                    repeat: false
                                                    onTriggered: linuxcue.setVirtuosoBand(liveBandIndex, Math.round(eqSlider.value), autoLiveWrite)
                                                }
                                                Slider {
                                                    id: eqSlider
                                                    Layout.fillHeight: true
                                                    Layout.preferredWidth: 28
                                                    orientation: Qt.Vertical
                                                    from: -36
                                                    to: 36
                                                    stepSize: 1
                                                    value: modelData
                                                    onMoved: {
                                                        eqSliderLiveTimer.restart()
                                                    }
                                                    onPressedChanged: {
                                                        if (!pressed) {
                                                            eqSliderLiveTimer.stop()
                                                            linuxcue.setVirtuosoBand(liveBandIndex, Math.round(value), autoLiveWrite)
                                                        }
                                                    }
                                                }
                                                Text {
                                                    Layout.alignment: Qt.AlignHCenter
                                                    text: ["31", "62", "125", "250", "500", "1k", "2k", "4k", "8k", "16k"][index]
                                                    color: "#9fb6bb"
                                                    font.pixelSize: 12
                                                }
                                            }
                                        }
                                    }
                                }
                            }

                            Panel {
                                Layout.preferredWidth: 330
                                Layout.fillHeight: true
                                title: "Headset-Regler"
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 18
                                    anchors.topMargin: 54
                                    spacing: 12
                                    Text { text: "Mic Sidetone"; color: "white"; font.bold: true; font.pixelSize: 13 }
                                    Slider {
                                        id: sidetoneSlider
                                        Layout.fillWidth: true
                                        from: 0
                                        to: 100
                                        value: linuxcue.virtuosoSidetone
                                        onPressedChanged: {
                                            if (!pressed)
                                                linuxcue.setVirtuosoControls(Math.round(value), Math.round(micSlider.value), sleepBox.model[sleepBox.currentIndex], voiceSwitch.checked, autoLiveWrite)
                                        }
                                    }
                                    Text { text: "Mic Level"; color: "white"; font.bold: true; font.pixelSize: 13 }
                                    Slider {
                                        id: micSlider
                                        Layout.fillWidth: true
                                        from: 0
                                        to: 100
                                        value: linuxcue.virtuosoMicLevel
                                        onPressedChanged: {
                                            if (!pressed)
                                                linuxcue.setVirtuosoControls(Math.round(sidetoneSlider.value), Math.round(value), sleepBox.model[sleepBox.currentIndex], voiceSwitch.checked, autoLiveWrite)
                                        }
                                    }
                                    Text { text: "Sleep Timer"; color: "white"; font.bold: true; font.pixelSize: 13 }
                                    ComboBox {
                                        id: sleepBox
                                        Layout.fillWidth: true
                                        model: [5, 10, 20, 30, 60]
                                        currentIndex: sleepTimerIndex(linuxcue.virtuosoSleepTimer)
                                        textRole: ""
                                        onActivated: linuxcue.setVirtuosoControls(Math.round(sidetoneSlider.value), Math.round(micSlider.value), model[currentIndex], voiceSwitch.checked, autoLiveWrite)
                                    }
                                    Switch {
                                        id: voiceSwitch
                                        text: "Voice Prompts"
                                        checked: linuxcue.virtuosoVoicePrompts
                                        onToggled: linuxcue.setVirtuosoControls(Math.round(sidetoneSlider.value), Math.round(micSlider.value), sleepBox.model[sleepBox.currentIndex], checked, autoLiveWrite)
                                    }
                                    Button { Layout.fillWidth: true; text: "Flat EQ"; onClicked: linuxcue.applyVirtuosoFlatEq() }
                                    Button { Layout.fillWidth: true; text: "Apply Linux EQ"; highlighted: true; onClicked: linuxcue.applyVirtuosoLinuxEq() }
                                    Button { Layout.fillWidth: true; text: "Native PipeWire EQ"; onClicked: linuxcue.applyVirtuosoPipeWireEq() }
                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 86
                                        radius: 10
                                        color: "#07130f"
                                        border.color: "#264438"
                                        Text {
                                            anchors.fill: parent
                                            anchors.margins: 12
                                            text: "EasyEffects bleibt als Live-Fallback. Native PipeWire EQ erstellt eine linuxcue Filter-Chain ohne EasyEffects-GUI."
                                            color: "#d7edf0"
                                            wrapMode: Text.WordWrap
                                            font.pixelSize: 12
                                        }
                                    }
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 16
                            color: "#0d1113"
                            border.color: "#24363d"
                            visible: virtuosoSection === "nvidia"
                            Text {
                                anchors.centerIn: parent
                                width: parent.width - 80
                                text: "NVIDIA-/Broadcast-Integration ist als Platzhalter angelegt. Sobald wir echte Einstellungen anbinden, landet sie hier getrennt vom Equalizer."
                                color: "#9fb6bb"
                                horizontalAlignment: Text.AlignHCenter
                                wrapMode: Text.WordWrap
                                font.pixelSize: 16
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 18
                color: "#0b1114"
                border.color: "#24363d"
                visible: !showK95Dashboard && !showM65Dashboard && !showVirtuosoDashboard

                Column {
                    anchors.centerIn: parent
                    spacing: 12
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: linuxcue.devices.length === 0 ? "Keine passenden verbundenen Geraete im aktiven Profil." : "Bitte oben ein verbundenes Geraet aus diesem Profil auswaehlen."
                        color: "#d7edf0"
                        font.pixelSize: 18
                        font.bold: true
                    }
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: 520
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                        text: "Links waehlst du nur das Hauptprofil. Die Geraetekacheln erscheinen oben nur, wenn das Profil dieses Geraet enthaelt und es per Hotplug verbunden ist."
                        color: "#91aeb2"
                        font.pixelSize: 14
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 86
                radius: 16
                color: "#101817"
                border.color: "#283b36"

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 18
                    ColumnLayout {
                        spacing: 3
                        Text { text: "Live Write"; color: "#ffcf55"; font.bold: true; font.pixelSize: 20 }
                        Text { text: "Aenderungen werden nach Check direkt an die Hardware geschickt."; color: "#9eb5b0"; font.pixelSize: 13 }
                    }
                    CheckBox {
                        checked: autoLiveWrite
                        text: "Auto Live Write"
                        onToggled: autoLiveWrite = checked
                    }
                    LiveStep { label: "1 Validate"; state: "OK" }
                    LiveStep { label: "2 Diff"; state: "Ready" }
                    LiveStep { label: "3 Backup"; state: "Local" }
                    LiveStep { label: "4 Write"; state: "Armed" }
                    Item { Layout.fillWidth: true }
                    Button { text: "Live Write"; highlighted: true; onClicked: linuxcue.writeLive() }
                    Button { text: "Refresh"; onClicked: linuxcue.refresh() }
                }
            }
        }
    }

    function zoneTitle(zone) {
        if (zone === "all")
            return "Alle"
        if (zone === "wasd")
            return "WASD"
        if (zone === "qwerdf")
            return "QWERDF"
        if (zone === "gkeys")
            return "G-Tasten"
        if (zone === "numpad")
            return "Ziffernblock"
        if (zone === "arrows")
            return "Pfeiltasten"
        if (zone === "numbers")
            return "1-6"
        if (zone.indexOf("key:") === 0)
            return "Taste " + zone.substring(4).toUpperCase()
        return zone
    }

    Rectangle {
        width: 22
        height: 22
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        color: "transparent"
        border.color: resizeDrag.containsMouse ? "#12e8ff" : "transparent"

        Canvas {
            anchors.fill: parent
            onPaint: {
                var ctx = getContext("2d")
                ctx.clearRect(0, 0, width, height)
                ctx.strokeStyle = "#4f7078"
                ctx.lineWidth = 1
                for (var i = 0; i < 3; i++) {
                    ctx.beginPath()
                    ctx.moveTo(width - 4 - i * 6, height - 2)
                    ctx.lineTo(width - 2, height - 4 - i * 6)
                    ctx.stroke()
                }
            }
        }

        MouseArea {
            id: resizeDrag
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.SizeFDiagCursor
            onPressed: function(mouse) {
                if (window.startSystemResize(Qt.RightEdge | Qt.BottomEdge))
                    return
                resizeStartX = mouse.screenX
                resizeStartY = mouse.screenY
                resizeStartWidth = window.width
                resizeStartHeight = window.height
            }
            onPositionChanged: function(mouse) {
                if (!pressed)
                    return
                window.width = Math.max(window.minimumWidth, resizeStartWidth + mouse.screenX - resizeStartX)
                window.height = Math.max(window.minimumHeight, resizeStartHeight + mouse.screenY - resizeStartY)
            }
        }
    }
}
