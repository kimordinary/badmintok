# 모바일 카카오 로그인 API 가이드

## 개요

모바일 앱에서 카카오 로그인을 구현하기 위한 REST API 엔드포인트입니다.

## API 엔드포인트

### 카카오 로그인 (모바일)

**POST** `/accounts/api/kakao/mobile/`

모바일 앱에서 카카오 SDK로 받은 `access_token`을 서버로 전송하여 로그인을 처리합니다.

#### 요청

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "access_token": "카카오에서 받은 access_token"
}
```

#### 응답

**성공 (200 OK):**
```json
{
  "success": true,
  "user": {
    "id": 1,
    "email": "user@example.com",
    "activity_name": "사용자명",
    "profile_image_url": "https://example.com/media/images/userprofile/kakao_1.jpg"
  },
  "session_id": "세션_ID",
  "requires_real_name": false
}
```

**실패 (400 Bad Request):**
```json
{
  "success": false,
  "error": "에러 메시지"
}
```

#### 필드 설명

- `success`: 요청 성공 여부 (boolean)
- `user`: 사용자 정보 객체
  - `id`: 사용자 ID
  - `email`: 이메일 주소
  - `activity_name`: 활동명 (닉네임)
  - `profile_image_url`: 프로필 이미지 URL (없으면 null)
- `session_id`: 세션 ID (쿠키로도 전달됨)
- `requires_real_name`: 실명 입력 필요 여부 (boolean)
  - `true`: 실명 입력 페이지로 이동 필요
  - `false`: 정상 로그인 완료

## 모바일 앱 구현 가이드

### iOS (Swift)

```swift
import KakaoSDKAuth
import KakaoSDKUser

// 1. 카카오 로그인
UserApi.shared.loginWithKakaoTalk { (oauthToken, error) in
    if let error = error {
        print(error)
        return
    }
    
    guard let accessToken = oauthToken?.accessToken else {
        return
    }
    
    // 2. 서버로 access_token 전송
    let url = URL(string: "https://yourdomain.com/accounts/api/kakao/mobile/")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    
    let body: [String: Any] = ["access_token": accessToken]
    request.httpBody = try? JSONSerialization.data(withJSONObject: body)
    
    URLSession.shared.dataTask(with: request) { data, response, error in
        if let error = error {
            print("Error: \(error)")
            return
        }
        
        guard let data = data,
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let success = json["success"] as? Bool,
              success == true else {
            print("Login failed")
            return
        }
        
        // 3. 세션 쿠키 저장 (URLSession이 자동으로 처리)
        // 4. 사용자 정보 저장
        if let user = json["user"] as? [String: Any] {
            let userId = user["id"] as? Int
            let email = user["email"] as? String
            let activityName = user["activity_name"] as? String
            // 사용자 정보 저장
        }
        
        // 5. 실명 입력 필요 여부 확인
        if let requiresRealName = json["requires_real_name"] as? Bool, requiresRealName {
            // 실명 입력 화면으로 이동
        } else {
            // 메인 화면으로 이동
        }
    }.resume()
}
```

### Android (Kotlin)

```kotlin
import com.kakao.sdk.auth.model.OAuthToken
import com.kakao.sdk.user.UserApiClient

// 1. 카카오 로그인
val callback: (OAuthToken?, Throwable?) -> Unit = { token, error ->
    if (error != null) {
        Log.e("KakaoLogin", "로그인 실패", error)
        return@let
    }
    
    token?.accessToken?.let { accessToken ->
        // 2. 서버로 access_token 전송
        val url = "https://yourdomain.com/accounts/api/kakao/mobile/"
        val client = OkHttpClient()
        val json = JSONObject()
        json.put("access_token", accessToken)
        
        val requestBody = json.toString().toRequestBody("application/json".toMediaType())
        val request = Request.Builder()
            .url(url)
            .post(requestBody)
            .build()
        
        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                Log.e("KakaoLogin", "서버 요청 실패", e)
            }
            
            override fun onResponse(call: Call, response: Response) {
                val responseBody = response.body?.string()
                val json = JSONObject(responseBody)
                
                if (json.getBoolean("success")) {
                    // 3. 세션 쿠키 저장 (OkHttp가 자동으로 처리)
                    // 4. 사용자 정보 저장
                    val user = json.getJSONObject("user")
                    val userId = user.getInt("id")
                    val email = user.getString("email")
                    val activityName = user.getString("activity_name")
                    
                    // 5. 실명 입력 필요 여부 확인
                    val requiresRealName = json.getBoolean("requires_real_name")
                    if (requiresRealName) {
                        // 실명 입력 화면으로 이동
                    } else {
                        // 메인 화면으로 이동
                    }
                } else {
                    val error = json.getString("error")
                    Log.e("KakaoLogin", "로그인 실패: $error")
                }
            }
        })
    }
}

// 카카오톡으로 로그인 시도
if (UserApiClient.instance.isKakaoTalkLoginAvailable(context)) {
    UserApiClient.instance.loginWithKakaoTalk(context, callback = callback)
} else {
    // 카카오 계정으로 로그인
    UserApiClient.instance.loginWithKakaoAccount(context, callback = callback)
}
```

### React Native

```javascript
import { login, getProfile } from '@react-native-seoul/kakao-login';
import AsyncStorage from '@react-native-async-storage/async-storage';

// 1. 카카오 로그인
const handleKakaoLogin = async () => {
  try {
    const token = await login();
    const accessToken = token.accessToken;
    
    // 2. 서버로 access_token 전송
    const response = await fetch('https://yourdomain.com/accounts/api/kakao/mobile/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        access_token: accessToken,
      }),
      credentials: 'include', // 쿠키 포함
    });
    
    const data = await response.json();
    
    if (data.success) {
      // 3. 세션 쿠키는 자동으로 저장됨 (credentials: 'include')
      // 4. 사용자 정보 저장
      await AsyncStorage.setItem('userId', data.user.id.toString());
      await AsyncStorage.setItem('userEmail', data.user.email);
      await AsyncStorage.setItem('activityName', data.user.activity_name);
      
      // 5. 실명 입력 필요 여부 확인
      if (data.requires_real_name) {
        // 실명 입력 화면으로 이동
        navigation.navigate('EnterRealName');
      } else {
        // 메인 화면으로 이동
        navigation.navigate('Home');
      }
    } else {
      console.error('로그인 실패:', data.error);
    }
  } catch (error) {
    console.error('카카오 로그인 오류:', error);
  }
};
```

## 웹 기반 카카오 로그인 (참고)

웹 브라우저에서는 기존 OAuth 2.0 방식의 엔드포인트를 사용합니다:

- **로그인 시작**: `GET /accounts/login/kakao/`
- **콜백 처리**: `GET /accounts/kakao/`

## 에러 처리

### 일반적인 에러 코드

- **400 Bad Request**: 요청 형식이 잘못되었거나 필수 파라미터가 누락됨
- **500 Internal Server Error**: 서버 내부 오류

### 에러 응답 예시

```json
{
  "success": false,
  "error": "카카오 계정에서 이메일 정보를 제공하지 않았습니다."
}
```

## 보안 고려사항

1. **HTTPS 사용**: 프로덕션 환경에서는 반드시 HTTPS를 사용하세요.
2. **세션 관리**: 서버에서 세션 쿠키를 발급하므로, 이후 API 요청 시 쿠키를 포함해야 합니다.
3. **토큰 검증**: 서버는 카카오 API를 통해 `access_token`의 유효성을 검증합니다.

## 추가 정보

- 카카오 개발자 센터: https://developers.kakao.com/
- 카카오 로그인 가이드: https://developers.kakao.com/docs/latest/ko/kakaologin/rest-api
