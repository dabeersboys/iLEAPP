# Photos.sqlite
# Author:  Scott Koenig, assisted by past contributors
# Version: 1.0
#
#   Description:
#   Parses Assets in iCloud Shared Photo Library with contributor information from PhotoData/Photos.sqlite ZSHARE Table
#   and supports iOS 16-17. Parses basic asset data and iCloud SPL and contributor information.
#   If you are attempting to match SPL count with results please check hidden, trashed, and burst assets.
#   This parser is based on research and SQLite Queries written by Scott Koenig
#   https://theforensicscooter.com/ and queries found at https://github.com/ScottKjr3347
#

import os
from datetime import datetime
import pytz
import json
import shutil
import base64
from PIL import Image
from pillow_heif import register_heif_opener
import glob
import sys
import stat
from pathlib import Path
import sqlite3
import nska_deserialize as nd
import scripts.artifacts.artGlobals
from packaging import version
from scripts.artifact_report import ArtifactHtmlReport
from scripts.ilapfuncs import logfunc, tsv, timeline, kmlgen, is_platform_windows, media_to_html, open_sqlite_db_readonly


def get_ph32icldsplassetsphdapsql(files_found, report_folder, seeker, wrap_text, timezone_offset):
    for file_found in files_found:
        file_found = str(file_found)
        
        if file_found.endswith('Photos.sqlite'):
            break
      
    if report_folder.endswith('/') or report_folder.endswith('\\'):
        report_folder = report_folder[:-1]
    iosversion = scripts.artifacts.artGlobals.versionf
    if version.parse(iosversion) < version.parse("16"):
        logfunc("Unsupported version for iCloud Shared Photo Library assets from PhotoData/Photos.sqlite"
                " from iOS " + iosversion)
    if version.parse(iosversion) >= version.parse("16"):
        file_found = str(files_found[0])
        db = open_sqlite_db_readonly(file_found)
        cursor = db.cursor()

        cursor.execute("""
        SELECT
        DateTime(zAsset.ZDATECREATED + 978307200, 'UNIXEPOCH') AS 'zAsset-Date Created',
        CASE zAsset.ZACTIVELIBRARYSCOPEPARTICIPATIONSTATE
            WHEN 0 THEN '0-Asset-Not-In-Active-SPL-0'
            WHEN 1 THEN '1-Asset-In-Active-SPL-1'
            ELSE 'Unknown-New-Value!: ' || zAsset.ZACTIVELIBRARYSCOPEPARTICIPATIONSTATE || ''
        END AS 'zAsset-Active Library Scope Participation State',
        zAsset.Z_PK AS 'zAsset-zPK',
        zAsset.ZDIRECTORY AS 'zAsset-Directory/Path',
        zAsset.ZFILENAME AS 'zAsset-Filename',
        zAddAssetAttr.ZORIGINALFILENAME AS 'zAddAssetAttr- Original Filename',
        zCldMast.ZORIGINALFILENAME AS 'zCldMast- Original Filename',
        zAddAssetAttr.ZSYNDICATIONIDENTIFIER AS 'zAddAssetAttr- Syndication Identifier-SWY-Files',
        CASE zAsset.ZSYNDICATIONSTATE
            WHEN 0 THEN '0-PhDaPs-NA_or_SyndPs-Received-SWY_Synd_Asset-0'
            WHEN 1 THEN '1-SyndPs-Sent-SWY_Synd_Asset-1'
            WHEN 2 THEN '2-SyndPs-Manually-Saved_SWY_Synd_Asset-2'
            WHEN 3 THEN '3-SyndPs-STILLTESTING_Sent-SWY-3'
            WHEN 8 THEN '8-SyndPs-Linked_Asset_was_Visible_On-Device_User_Deleted_Link-8'
            WHEN 9 THEN '9-SyndPs-STILLTESTING_Sent_SWY-9'
            WHEN 10 THEN '10-SyndPs-Manually-Saved_SWY_Synd_Asset_User_Deleted_From_LPL-10'
            ELSE 'Unknown-New-Value!: ' || zAsset.ZSYNDICATIONSTATE || ''
        END AS 'zAsset-Syndication State',
        CASE zAsset.ZBUNDLESCOPE
            WHEN 0 THEN '0-iCldPhtos-ON-AssetNotInSharedAlbum_or_iCldPhtos-OFF-AssetOnLocalDevice-0'
            WHEN 1 THEN '1-SharediCldLink_CldMastMomentAsset-1'
            WHEN 2 THEN '2-iCldPhtos-ON-AssetInCloudSharedAlbum-2'
            WHEN 3 THEN '3-iCldPhtos-ON-AssetIsInSWYConversation-3'
            ELSE 'Unknown-New-Value!: ' || zAsset.ZBUNDLESCOPE || ''
        END AS 'zAsset-Bundle Scope',
        CASE zAddAssetAttr.ZIMPORTEDBY
            WHEN 0 THEN '0-Cloud-Other-0'
            WHEN 1 THEN '1-Native-Back-Camera-1'
            WHEN 2 THEN '2-Native-Front-Camera-2'
            WHEN 3 THEN '3-Third-Party-App-3'
            WHEN 4 THEN '4-StillTesting-4'
            WHEN 5 THEN '5-PhotoBooth_PL-Asset-5'
            WHEN 6 THEN '6-Third-Party-App-6'
            WHEN 7 THEN '7-iCloud_Share_Link-CMMAsset-7'
            WHEN 8 THEN '8-System-Package-App-8'
            WHEN 9 THEN '9-Native-App-9'
            WHEN 10 THEN '10-StillTesting-10'
            WHEN 11 THEN '11-StillTesting-11'
            WHEN 12 THEN '12-SWY_Syndication_PL-12'
            ELSE 'Unknown-New-Value!: ' || zAddAssetAttr.ZIMPORTEDBY || ''
        END AS 'zAddAssetAttr-Imported by',
        zExtAttr.ZCAMERAMAKE AS 'zExtAttr-Camera Make',
        zExtAttr.ZCAMERAMODEL AS 'zExtAttr-Camera Model',
        zAddAssetAttr.ZIMPORTEDBYBUNDLEIDENTIFIER AS 'zAddAssetAttr- Imported by Bundle Identifier',
        zAddAssetAttr.ZIMPORTEDBYDISPLAYNAME AS 'zAddAssetAttr- Imported By Display Name',
        CASE zAsset.ZVISIBILITYSTATE
            WHEN 0 THEN '0-Visible-PL-CameraRoll-0'
            WHEN 2 THEN '2-Not-Visible-PL-CameraRoll-2'
            ELSE 'Unknown-New-Value!: ' || zAsset.ZVISIBILITYSTATE || ''
        END AS 'zAsset-Visibility State',
        CASE zAsset.ZSAVEDASSETTYPE
            WHEN 0 THEN '0-Saved-via-other-source-0'
            WHEN 1 THEN '1-StillTesting-1'
            WHEN 2 THEN '2-StillTesting-2'
            WHEN 3 THEN '3-PhDaPs-Asset_or_SyndPs-Asset_NoAuto-Display-3'
            WHEN 4 THEN '4-Photo-Cloud-Sharing-Data-Asset-4'
            WHEN 5 THEN '5-PhotoBooth_Photo-Library-Asset-5'
            WHEN 6 THEN '6-Cloud-Photo-Library-Asset-6'
            WHEN 7 THEN '7-StillTesting-7'
            WHEN 8 THEN '8-iCloudLink_CloudMasterMomentAsset-8'
            WHEN 12 THEN '12-SyndPs-SWY-Asset_Auto-Display_In_CameraRoll-12'
            ELSE 'Unknown-New-Value!: ' || zAsset.ZSAVEDASSETTYPE || ''
        END AS 'zAsset-Saved Asset Type',
        CASE zAddAssetAttr.ZSHARETYPE
            WHEN 0 THEN '0-Not_Shared-or-Shared_via_Phy_Device_StillTesting-0'
            WHEN 1 THEN '1-Shared_via_iCldPhotos_Web-or-Other_Device_StillTesting-1'
            ELSE 'Unknown-New-Value!: ' || zAddAssetAttr.ZSHARETYPE || ''
        END AS 'zAddAssetAttr-Share Type',
        DateTime(zAsset.ZSORTTOKEN + 978307200, 'UNIXEPOCH') AS 'zAsset- SortToken -CameraRoll',
        DateTime(zAsset.ZADDEDDATE + 978307200, 'UNIXEPOCH') AS 'zAsset-Added Date',        
        DateTime(zCldMast.ZCREATIONDATE + 978307200, 'UNIXEPOCH') AS 'zCldMast-Creation Date',
        zAddAssetAttr.ZTIMEZONENAME AS 'zAddAssetAttr-Time Zone Name',
        zAddAssetAttr.ZEXIFTIMESTAMPSTRING AS 'zAddAssetAttr-EXIF-String',
        DateTime(zAsset.ZMODIFICATIONDATE + 978307200, 'UNIXEPOCH') AS 'zAsset-Modification Date',
        DateTime(zAddAssetAttr.ZLASTVIEWEDDATE + 978307200, 'UNIXEPOCH') AS 'zAddAssetAttr-Last Viewed Date',
        DateTime(zAsset.ZLASTSHAREDDATE + 978307200, 'UNIXEPOCH') AS 'zAsset-Last Shared Date',
        CASE zAsset.ZHIDDEN
            WHEN 0 THEN '0-Asset Not Hidden-0'
            WHEN 1 THEN '1-Asset Hidden-1'
            ELSE 'Unknown-New-Value!: ' || zAsset.ZHIDDEN || ''
        END AS 'zAsset-Hidden',
        CASE zAsset.ZAVALANCHEPICKTYPE
            WHEN 0 THEN '0-NA/Single_Asset_Burst_UUID-0_RT'
            WHEN 2 THEN '2-Burst_Asset_Not_Selected-2_RT'
            WHEN 4 THEN '4-Burst_Asset_PhotosApp_Picked_KeyImage-4_RT'
            WHEN 8 THEN '8-Burst_Asset_Selected_for_LPL-8_RT'
            WHEN 16 THEN '16-Top_Burst_Asset_inStack_KeyImage-16_RT'
            WHEN 32 THEN '32-StillTesting-32_RT'
            WHEN 52 THEN '52-Burst_Asset_Visible_LPL-52'
            ELSE 'Unknown-New-Value!: ' || zAsset.ZAVALANCHEPICKTYPE || ''
        END AS 'zAsset-Avalanche_Pick_Type/BurstAsset',
        CASE zAddAssetAttr.ZCLOUDAVALANCHEPICKTYPE
            WHEN 0 THEN '0-NA/Single_Asset_Burst_UUID-0_RT'
            WHEN 2 THEN '2-Burst_Asset_Not_Selected-2_RT'
            WHEN 4 THEN '4-Burst_Asset_PhotosApp_Picked_KeyImage-4_RT'
            WHEN 8 THEN '8-Burst_Asset_Selected_for_LPL-8_RT'
            WHEN 16 THEN '16-Top_Burst_Asset_inStack_KeyImage-16_RT'
            WHEN 32 THEN '32-StillTesting-32_RT'
            WHEN 52 THEN '52-Burst_Asset_Visible_LPL-52'
            ELSE 'Unknown-New-Value!: ' || zAddAssetAttr.ZCLOUDAVALANCHEPICKTYPE || ''
        END AS 'zAddAssetAttr-Cloud_Avalanche_Pick_Type/BurstAsset',
        CASE zAsset.ZTRASHEDSTATE
            WHEN 0 THEN '0-Asset Not In Trash/Recently Deleted-0'
            WHEN 1 THEN '1-Asset In Trash/Recently Deleted-1'
            ELSE 'Unknown-New-Value!: ' || zAsset.ZTRASHEDSTATE || ''
        END AS 'zAsset-Trashed State/LocalAssetRecentlyDeleted',
        DateTime(zAsset.ZTRASHEDDATE + 978307200, 'UNIXEPOCH') AS 'zAsset-Trashed Date',
        zAsset.ZTRASHEDBYPARTICIPANT AS 'zAsset-Trashed by Participant= zShareParticipant_zPK',
        CASE zAddAssetAttr.ZSHARETYPE
            WHEN 0 THEN '0-Not_Shared-or-Shared_via_Phy_Device_StillTesting-0'
            WHEN 1 THEN '1-Shared_via_iCldPhotos_Web-or-Other_Device_StillTesting-1'
            ELSE 'Unknown-New-Value!: ' || zAddAssetAttr.ZSHARETYPE || ''
        END AS 'zAddAssetAttr-Share Type',
        zAddAssetAttr.Z_PK AS 'zAddAssetAttr-zPK',
        zAsset.ZUUID AS 'zAsset-UUID = store.cloudphotodb',
        zAddAssetAttr.ZMASTERFINGERPRINT AS 'zAddAssetAttr-Master Fingerprint',
        CASE SPLzSharePartic.ZISCURRENTUSER
            WHEN 0 THEN '0-Participant-Not_CloudStorageOwner-0'
            WHEN 1 THEN '1-Participant-Is_CloudStorageOwner-1'
            ELSE 'Unknown-New-Value!: ' || SPLzSharePartic.ZISCURRENTUSER || ''
        END AS 'SPLzSharePartic-Is Current User',
        CASE SPLzSharePartic.ZROLE
            WHEN 1 THEN '1-Participant-is-Owner-Role-1'
            WHEN 2 THEN '2-Participant-is-Invitee-Role-2'
            ELSE 'Unknown-New-Value!: ' || SPLzSharePartic.ZROLE || ''
        END AS 'SPLzSharePartic-Role',
        zAssetContrib.ZPARTICIPANT AS 'zAsstContrib-Participant= zSharePartic-zPK',
        SPLzSharePartic.ZEMAILADDRESS AS 'SPLzSharePartic-Email Address',
        SPLzSharePartic.ZPHONENUMBER AS 'SPLzSharePartic-Phone Number',        
        SPLzShare.ZTITLE AS 'SPLzShare-Title-SPL',
        SPLzShare.ZSHAREURL AS 'SPLzShare-Share URL-SPL',
        SPLzShare.ZSCOPEIDENTIFIER AS 'SPLzShare-Scope ID-SPL',
        DateTime(SPLzShare.ZCREATIONDATE + 978307200, 'UNIXEPOCH') AS 'SPLzShare-Creation Date-SPL',
        DateTime(SPLzShare.ZEXPIRYDATE + 978307200, 'UNIXEPOCH') AS 'SPLzShare-Expiry Date-SPL',
        SPLzShare.ZCLOUDPHOTOCOUNT AS 'SPLzShare-Cloud Photo Count-SPL',
        SPLzShare.ZCOUNTOFASSETSADDEDBYCAMERASMARTSHARING AS 'SPLzShare-Assets AddedByCamera SmartSharing',
        SPLzShare.ZCLOUDVIDEOCOUNT AS 'SPLzShare-Cloud Video Count-SPL'
        FROM ZASSET zAsset
          LEFT JOIN ZADDITIONALASSETATTRIBUTES zAddAssetAttr ON zAddAssetAttr.Z_PK = zAsset.ZADDITIONALATTRIBUTES
          LEFT JOIN ZEXTENDEDATTRIBUTES zExtAttr ON zExtAttr.Z_PK = zAsset.ZEXTENDEDATTRIBUTES
          LEFT JOIN ZCLOUDMASTER zCldMast ON zAsset.ZMASTER = zCldMast.Z_PK
          LEFT JOIN ZSHARE SPLzShare ON SPLzShare.Z_PK = zAsset.ZLIBRARYSCOPE
          LEFT JOIN ZASSETCONTRIBUTOR zAssetContrib ON zAssetContrib.Z3LIBRARYSCOPEASSETCONTRIBUTORS = zAsset.Z_PK
          LEFT JOIN ZSHAREPARTICIPANT SPLzSharePartic ON SPLzSharePartic.Z_PK = zAssetContrib.ZPARTICIPANT
        WHERE zAsset.ZACTIVELIBRARYSCOPEPARTICIPATIONSTATE = 1
        ORDER BY zAsset.ZDATECREATED     
        """)

        all_rows = cursor.fetchall()
        usageentries = len(all_rows)
        data_list = []
        counter = 0
        if usageentries > 0:
            for row in all_rows:
                data_list.append((row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9],
                                  row[10], row[11], row[12], row[13], row[14], row[15], row[16], row[17], row[18],
                                  row[19], row[20], row[21], row[22], row[23], row[24], row[25], row[26], row[27],
                                  row[28], row[29], row[30], row[31], row[32], row[33], row[34], row[35], row[36],
                                  row[37], row[38], row[39], row[40], row[41], row[42], row[43], row[44], row[45],
                                  row[46], row[47], row[48]))

                counter += 1

            description = 'Parses Assets in iCloud Shared Photo Library with contributor information from' \
                          ' PhotoData/Photos.sqlite ZSHARE Table and supports iOS 16-17.' \
                          ' Parses basic asset data and iCloud SPL and contributor information.' \
                          ' If you are attempting to match SPL count with results please check' \
                          ' hidden, trashed, and burst assets.'
            report = ArtifactHtmlReport('Photos.sqlite-iCloud_Shared_Methods')
            report.start_artifact_report(report_folder, 'Ph32-iCld Shared Photo Lib Assets-PhDaPsql', description)
            report.add_script()
            data_headers = ('zAsset-Date Created',
                            'zAsset-Active Library Scope Participation State',
                            'zAsset-zPK',
                            'zAsset-Directory/Path',
                            'zAsset-Filename',
                            'zAddAssetAttr- Original Filename',
                            'zCldMast- Original Filename',
                            'zAddAssetAttr- Syndication Identifier-SWY-Files',
                            'zAsset-Syndication State',
                            'zAsset-Bundle Scope',
                            'zAddAssetAttr-Imported by',
                            'zExtAttr-Camera Make',
                            'zExtAttr-Camera Model',
                            'zAddAssetAttr.Imported by Bundle Identifier',
                            'zAddAssetAttr-Imported By Display Name',
                            'zAsset-Visibility State',
                            'zAsset-Saved Asset Type',
                            'zAddAssetAttr-Share Type',
                            'zAsset- SortToken -CameraRoll',
                            'zAsset-Added Date',
                            'zCldMast-Creation Date',
                            'zAddAssetAttr-Time Zone Name',
                            'zAddAssetAttr-EXIF-String',
                            'zAsset-Modification Date',
                            'zAddAssetAttr-Last Viewed Date',
                            'zAsset-Last Shared Date',
                            'zAsset-Hidden',
                            'zAsset-Avalanche_Pick_Type/BurstAsset',
                            'zAddAssetAttr-Cloud_Avalanche_Pick_Type/BurstAsset',
                            'zAsset-Trashed State/LocalAssetRecentlyDeleted',
                            'zAsset-Trashed Date',
                            'zAsset-Trashed by Participant= zShareParticipant_zPK',
                            'zAddAssetAttr-Share Type',
                            'zAddAssetAttr-zPK',
                            'zAsset-UUID = store.cloudphotodb',
                            'zAddAssetAttr-Master Fingerprint',
                            'SPLzSharePartic-Is Current User',
                            'SPLzSharePartic-Role',
                            'zAsstContrib-Participant= zSharePartic-zPK',
                            'SPLzSharePartic-Email Address',
                            'SPLzSharePartic-Phone Number',
                            'SPLzShare-Title-SPL',
                            'SPLzShare-Share URL-SPL',
                            'SPLzShare-Scope ID-SPL',
                            'SPLzShare-Creation Date-SPL',
                            'SPLzShare-Expiry Date-SPL',
                            'SPLzShare-Cloud Photo Count-SPL',
                            'SPLzShare-Assets AddedByCamera SmartSharing',
                            'SPLzShare-Cloud Video Count-SPL')
            report.write_artifact_data_table(data_headers, data_list, file_found)
            report.end_artifact_report()

            tsvname = 'Ph32-iCld Shared Photo Lib Assets-PhDaPsql'
            tsv(report_folder, data_headers, data_list, tsvname)

            tlactivity = 'Ph32-iCld Shared Photo Lib Assets-PhDaPsql'
            timeline(report_folder, tlactivity, data_list, data_headers)

        else:
            logfunc('No assets in iCloud Shared Photo Library found in PhotoData/Photos.sqlite ZSHARE table')

        db.close()
        return


__artifacts_v2__ = {
    'Ph32-iCloud SPL Assets with Contributor-PhDaPsql': {
        'name': 'PhDaPL Photos.sqlite 32 iCld Shared Photo Library Assets with Contributor',
        'description': 'Parses Assets in iCloud Shared Photo Library with contributor information from'
                       ' PhotoData/Photos.sqlite ZSHARE Table and supports iOS 16-17.'
                       ' Parses basic asset data and iCloud SPL and contributor information.'
                       ' If you are attempting to match SPL count with results please check'
                       ' hidden, trashed, and burst assets.',
        'author': 'Scott Koenig https://theforensicscooter.com/',
        'version': '1.0',
        'date': '2024-04-14',
        'requirements': 'Acquisition that contains PhotoData/Photos.sqlite',
        'category': 'Photos.sqlite-iCloud_Shared_Methods',
        'notes': '',
        'paths': ('*/mobile/Media/PhotoData/Photos.sqlite'),
        'function': 'get_ph32icldsplassetsphdapsql'
    }
}