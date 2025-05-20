import React from "react"
import type { SettingsInitialDataType } from "./CustomComparison"

type SettingsProp = {
    data: SettingsInitialDataType
}

const Settings: React.FC<SettingsProp> = ({ data }) => {

    console.log("Rerender - settings component")

    return (
        <div className="space-y-3 p-3 bg-blue-100/50">
            <p>
                Theme: {data.theme}
            </p>
            <p>
                Notifications: {data.notifications}
            </p>
            <p>
                FontSize: {data.fontSize}
            </p>
        </div>
    )
} 

const MemoizedSettings = React.memo(
    Settings,
    (prevProps, nextProps)=>{
        const isThemeEqual = prevProps.data.theme === nextProps.data.theme
        const isNotificationsEqual = prevProps.data.notifications === nextProps.data.notifications
        const isFontSizeEqual = prevProps.data.fontSize === nextProps.data.fontSize

        return isThemeEqual && isNotificationsEqual && isFontSizeEqual
    }
)

export default MemoizedSettings