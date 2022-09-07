#pragma once

#ifdef __cplusplus
extern "C"
{
#endif                                                                                                  /* __cplusplus */
    int MakeTWCASignPasswd(const char *out, int *outlen, const char *propertyFile, const char *passwd); // 產生加密的 pfx 密碼

    int TWCASignInitial(const char *propertyFile, const char *encedPfxPasswd);
    char *GetPkiVersion();
    int GetErrorCode();
    char *GetErrorMsg();

    int SignPkcs7(const char *plain, const char *encoding);
    int SignPkcs7Bin(unsigned char *data, int datalen);
    int SignPkcs7File(const char *pkcs7Filename);

    char *GetSignedPkcs7();

    char *GetSignerCertB64();
    char *GetSignerCertSubjectCN();
    char *GetSignerCertSubject();
    char *GetSignerCertIssuer();
    char *GetSignerCertNotBefore();
    char *GetSignerCertNotAfter();
    char *GetSignerCertSerial();
    char *GetSignerCertFinger();
#ifdef __cplusplus
}
#endif /* __cplusplus */
