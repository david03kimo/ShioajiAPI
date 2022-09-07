#pragma once

#ifdef __cplusplus
extern "C"
{
#endif

#define RTN_SUCCESS 0 // 成功

// 檔案 I/O
#define RTN_CREATE_FOLDER 1001           // 無法建立目錄
#define RTN_FILE_READ 1002               // 檔案無法讀取
#define RTN_FILE_WRITE 1003              // 檔案無法寫入
#define RTN_PFX_FILE_NOT_FOUND 1101      // 憑證檔不存在
#define RTN_PFX_FILE_READ 1102           // 憑證檔無法讀取
#define RTN_PFX_FILE_WRITE 1103          // 憑證檔無法寫入
#define RTN_PROPERTY_FILE_NOT_FOUND 1201 // PROPERTY 檔不存在
#define RTN_PROPERTY_FILE_READ 1202      // PROPERTY 檔無法讀取
#define RTN_PROPERTY_FILE_WRITE 1203     // PROPERTY 檔無法寫入

#define RTN_ERROR 5001              // 一般錯誤
#define RTN_MEMALLOC_ERROR 5002     // 配置記憶體發生錯誤
#define RTN_BUFFER_TOO_SMALL 5003   // 配置記憶體不足
#define RTN_FUNCTION_UNSUPPORT 5004 // 不支援的功能
#define RTN_INVALID_PARAM 5005      // 錯誤的參數
#define RTN_INVALID_HANDLE 5006     // Handle錯誤
#define RTN_LIB_EXPIRE 5007         // 試用版期限已過
#define RTN_BASE64_ERROR 5008       // Base64 編碼錯誤

#define RTN_CERT_NOT_FOUND 5010             // 無法在憑證區(或憑證檔)中,找到指定憑證
#define RTN_CERT_EXPIRED 5011               // 憑證已過期
#define RTN_CERT_NOT_YET_VALID 5012         // 憑證尚未生效,無法使用
#define RTN_CERT_EXPIRE_OR_NOT_YET_USE 5013 // 憑證可能過期或無法使用
#define RTN_CERT_INVALID_SUBJECT 5014       // 憑證主旨錯誤
#define RTN_CERT_NOISSUER 5015              // 無法找到憑證發行者
#define RTN_CERT_BAD_SIGNATURE 5016         // 不合法的憑證簽章
#define RTN_CERT_INVALID_KEYUSAGE 5017      // 憑證用途(加解密,簽驗章)不合適
#define RTN_CERT_NOT_REGISTER 5018          // 憑證尚未註冊, 無法找到指定憑證

#define RTN_CERT_REVOKED 5020             // 憑證已廢止
#define RTN_CERT_KEY_COMPROMISED 5021     // 憑證已廢止(金鑰洩露)
#define RTN_CERT_CA_COMPROMISED 5022      // 憑證已廢止(CA compromised)
#define RTN_CERT_AFFILIATION_CHANGED 5023 // 憑證已廢止(聯盟已變更)
#define RTN_CERT_SUPERSEDED 5024          // 憑證已廢止(已取代)
#define RTN_CERT_CESSATION 5025           // 憑證已廢止(已停止)
#define RTN_CERT_HOLD 5026                // 憑證保留或暫禁
#define RTN_CERT_REMOVEFROMCRL 5028       // 憑證已被CRL廢止

#define RTN_CRL_EXPIRED 5030       // CRL已過期
#define RTN_CRL_NOT_YET_VALID 5031 // 不合法的CRL
#define RTN_CRL_NOT_FOUND 5032     // 無法找到CRL
#define RTN_CRL_BAD_SIGNATURE 5034 // CRL簽章值錯誤
#define RTN_GET_DIGEST_ERROR 5035  // Digest錯誤
#define RTN_BAD_SIGNATURE 5036     // 不合法的簽章
#define RTN_BAD_CONTENT 5037       // 內容錯誤

#define RTN_INVALID_CERT 5040             // 憑證格式錯誤
#define RTN_INVALID_CRL 5041              // CRL格式錯誤
#define RTN_INVALID_PKCS7 5042            // 錯誤的PKCS7格式
#define RTN_INVALID_KEY 5043              // Key的格式錯誤
#define RTN_INVALID_CERTREQ 5044          // 不合法的PKCS10格式
#define RTN_INVALID_FORMAT 5045           // 不合適的格式
#define RTN_INVALID_CSP_NAME 5046         // CSP 名稱錯誤
#define RTN_UNSUPPORT_CSP_NAME 5047       // 作業系統不支援此 CSP
#define RTN_UNSUPPORT_FORCE_CSP_NAME 5048 // 強制使用 AES/SHA2 CSP 失敗, 作業系統不支援
#define RTN_RESET_FORCE_CSP_NAME 5049     // 強制使用 AES/SHA2 CSP 情況下, 禁止變更使用其他 CSP

#define RTN_OBJ_NOT_FOUND 5050        // 物件不存在
#define RTN_PKCS7_NO_CONTENT 5051     // PKCS7內容沒有包含原文
#define RTN_PKCS7_NO_CERTIFICATE 5052 // PKCS7內容沒有包含憑證
#define RTN_PKCS7_NO_SIGNERINFO 5053  // PKCS7內容沒有包含簽章資訊

#define RTN_UNMATCH_CERT_KEY 5060      // 金鑰不存在
#define RTN_SIGN_ERROR 5061            // 簽章失敗
#define RTN_VERIFY_ERROR 5062          // 驗章失敗
#define RTN_ENCRYPT_ERROR 5063         // 加密失敗
#define RTN_DECRYPT_ERROR 5064         // 解密失敗
#define RTN_GENKEY_ERROR 5065          // 產生金鑰失敗
#define RTN_DELETE_USR_CERT_ERROR 5066 // 刪除憑證失敗
#define RTN_NO_SELECT_SIGNER_CERT 5067 // 執行簽章時, 尚未選擇簽章憑證

#define RTN_CAPI_OPERATION_CANCELED 5070 // 使用者按下"取消"按鈕
#define RTN_CAPI_PASSWD_INVALID 5071     // 密碼錯誤

#define RTN_XML_PARSE_ERROR 5080  // 無法剖析XML文件
#define RTN_XML_TAG_NOTFOUND 5081 // 無法在XML中,找到指定的標籤名稱

#define RTN_CAPI_ENUM_PROVIDERS 5200       // 列舉 CSP 發生錯誤
#define RTN_CAPI_OPEN_MY_STORE_ERROR 5201  // 開啟"個人憑證區"失敗
#define RTN_CAPI_CREATECHAIN_ERROR 5202    // 憑證鏈不存在
#define RTN_CAPI_ACQUIRE_CSP_ERROR 5203    // 無法取得CSP資源
#define RTN_CAPI_NO_PRIVATE_KEY 5204       // 找不到關聯的私密金鑰
#define RTN_CAPI_UNEXPORTABLE 5205         // 關聯的私密金鑰已被標記成"不能匯出"
#define RTN_CAPI_MY_STORE_ACCESS_DENY 5206 // 個人憑證區存取被拒
#define RTN_CAPI_P12_FORMAT_ERROR 5207     // PKCS12檔案格式錯誤
#define RTN_CAPI_P12_PASSWD_ERROR 5208     // PKCS12 密碼錯誤
#define RTN_CAPI_PASSWD_NOT_MATCH 5209     // 新密碼及確認密碼不一致
#define RTN_CAPI_STORE_ACCESS_DENY 5210    // PFX 或記憶體憑證區存取被拒
#define RTN_CAPI_CSP_ACCESS_DENY 5211      // CSP 存取被拒

#define RTN_CAPI_OPEN_ROOT_STORE_ERROR 5221   // 開啟"信任根憑證區"失敗
#define RTN_CAPI_OPEN_CA_STORE_ERROR 5222     // 開啟"信任中繼憑證區"失敗
#define RTN_CAPI_OPEN_TRUST_STORE_ERROR 5223  // 開啟"其他人憑證區"失敗
#define RTN_CAPI_CERT_CHAIN_UNTRUST 5224      // 憑證鏈有誤, 無法信任
#define RTN_CAPI_IC_CARD_NOT_READY 5225       //  IC 卡尚未備妥
#define RTN_CAPI_OPEN_MEMORY_STORE_ERROR 5226 // 開啟"記憶體憑證區"失敗

#define RTN_CAPI_INVALID_KEY_BITS 5301 // 金鑰長度錯誤
#define RTN_CAPI_GEN_RSA_KEY 5302      // 金鑰產生失敗
#define RTN_CAPI_GEN_PFX 5303          // 憑證交換檔產生失敗
#define RTN_CAPI_GEN_REQ 5304          // 憑證請求檔產生失敗
#define RTN_CAPI_ASN1_ENCODE 5305      // ASN1編碼失敗

#define RTN_CAPI_PFX_FILE_NOT_FOUND 5400 // 憑證交換檔讀不存在
#define RTN_CAPI_PFX_FILE_READ 5401      // 憑證交換檔讀取失敗
#define RTN_CAPI_PFX_FILE_WRITE 5402     // 憑證交換檔寫入失敗

#define RTN_UNICODE_ERROR 5901  // Unicode錯誤
#define RTN_FILE_NOT_FOUND 5902 // File Not Found
#define RTN_PATH_NOT_FOUND 5903 // Path Not Found
#define RTN_BAD_NETPATH 5904    // Network path was not found
#define RTN_LOGON_FAILURE 5905  // Unknown logon user name or bad password
#define RTN_ACCESS_DENIED 5906  // 使用者權限不足

#define RTN_XML_ERROR 7701                 // 一般錯誤
#define RTN_XML_INVALID_ALGORITHM 7704     // 所指定的演算法不正確
#define RTN_XML_CRYPT_FAIL 7705            // 執行簽驗章演算法時發生錯誤
#define RTN_XML_INCORRECT_SIGNATURE 7706   // 簽章值錯誤
#define RTN_XML_INCORRECT_REFERENCE 7707   // Reference的摘要值錯誤
#define RTN_XML_C14N_FAIL 7708             // 執行正規化演算法時發生錯誤
#define RTN_XML_TRANSFORM_FAIL 7709        // 執行Transform演算法時發生錯誤
#define RTN_XML_RESOLVER_FAIL 7710         // 執行Resolver時發生錯誤
#define RTN_XML_NO_SIGNATURE 7711          // 找不到簽章值
#define RTN_XML_PARSER_ERROR 7712          // 解析XML文件時發生錯誤
#define RTN_XML_URI_NOT_EXISTURI 7713      // 所指向的文件不存在或為空值
#define RTN_XML_X509DATA_MISMATCH 7714     // 憑證內容與<X509Data>的記載不符合
#define RTN_XML_ERROR_XML_DOC 7715         // XML文件不存在或格式錯誤
#define RTN_XML_INVALID_PARAM 7716         // 參數不正確
#define RTN_XML_INVALID_C14N_ALG 7717      // 不支援此C14N演算法
#define RTN_XML_INVALID_SIGNATURE_ALG 7718 // 不支援此簽章演算法
#define RTN_XML_INVALID_DIGEST_ALG 7719    // 不支援此摘要演算法

// 定義 PKCS#7 的錯誤碼
//#define RTN_NEW_PKCS7 = 8701; // 無法建立 PKCS7
//#define RTN_BAD_PKCS7 = 8702; // 尚未建立 PKCS7
//#define RTN_BAD_PKCS7_CONTENT = 8703; // 處理 PKCS7 時, 沒有本文資料, 無法執行
//#define RTN_BAD_ENCRYPT_CERT = 8704; // 錯誤的加密憑證
//#define RTN_DUP_ENCRYPT_CERT = 8705; // 重複的加密憑證

// 定義 PKCS#12 的錯誤碼
#define RTN_P12_NOT_IMPORT 8706     // P12 檔尚未載入
#define RTN_P12_ALREADY_IMPORT 8707 // P12 檔早已載入

// 定義 加解密 的錯誤碼
#define RTN_INVALID_CIPHER_ALGOR 9001           // 加解密演算法錯誤
#define RTN_INVALID_CIPHER_FORMAT 9002          // 加解格式錯誤
#define RTN_INVALID_CIPHER_PASS_LENGTH 9003     // 加解密密碼長度錯誤
#define RTN_INVALID_CIPHER_ENCRYPT 9004         // 加密錯誤
#define RTN_INVALID_CIPHER_DECRYPT 9005         // 解密錯誤
#define RTN_INVALID_CIPHER_DECRYPT_NO_CERT 9006 // 解密錯誤, 找不到可用憑證

#define RTN_CRL_SERVICE_NOT_READY 25601  // 0x6401 CRL 服務尚未啟動, 無法驗證
#define RTN_CRL_VERIFY_PARAM 25602       // 0x6402 CRL 驗證參數錯誤, 無法驗證
#define RTN_CRL_VERIFY_NO_UCA_INFO 25603 // 0x6403 UCA 憑證不存在, 無法驗證

#define RTN_CRL_FILE_NOT_EXIST 25616 // 0x6410 CRL 無法取得, 無法驗證
#define RTN_CRL_FILE_FORMAT 25617    // 0x6411 CRL 格式錯誤, 無法驗證

#define RTN_CRL_UNLOADED 25632 // 0x6420 CRL 尚未取得, 無法驗證

#ifdef __cplusplus
}
#endif
