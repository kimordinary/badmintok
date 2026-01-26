# 모바일 구글 로그인 API 가이드

## 개요

모바일 앱에서 구글 로그인을 구현하기 위한 REST API 엔드포인트입니다.

## API 엔드포인트

### 구글 로그인 (모바일)

**POST** `/accounts/api/google/mobile/`

모바일 앱에서 구글 SDK로 받은 `access_token`을 서버로 전송하여 로그인을 처리합니다.

#### 요청

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "access_token": "구글에서 받은 access_token"
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
    "profile_image_url": "https://example.com/media/images/userprofile/google_1.jpg"
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
import GoogleSignIn

class ViewController: UIViewController {
    @IBAction func googleLogin(_ sender: UIButton) {
        guard let clientID = GIDSignIn.sharedInstance.clientID else { return }

        let config = GIDConfiguration(clientID: clientID)
        GIDSignIn.sharedInstance.configuration = config

        GIDSignIn.sharedInstance.signIn(withPresenting: self) { result, error in
            if let error = error {
                print("Google login error: \(error)")
                return
            }

            guard let user = result?.user,
                  let idToken = user.idToken?.tokenString else {
                return
            }

            // 여기서는 access_token 대신 idToken을 사용할 수도 있지만,
            // 서버 구현에 맞춰 accessToken 사용 예시를 제공합니다.
            let accessToken = user.accessToken.tokenString

            // 서버로 access_token 전송
            let url = URL(string: "https://yourdomain.com/accounts/api/google/mobile/")!
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

                // 세션 쿠키 저장 (URLSession이 자동으로 처리)
                // 사용자 정보 저장
                if let user = json["user"] as? [String: Any] {
                    let userId = user["id"] as? Int
                    let email = user["email"] as? String
                    let activityName = user["activity_name"] as? String
                    // 사용자 정보 저장
                }

                // 실명 입력 필요 여부 확인
                if let requiresRealName = json["requires_real_name"] as? Bool, requiresRealName {
                    // 실명 입력 화면으로 이동
                } else {
                    // 메인 화면으로 이동
                }
            }.resume()
        }
    }
}
```

### Android (Kotlin)

```kotlin
import com.google.android.gms.auth.api.signin.GoogleSignIn
import com.google.android.gms.auth.api.signin.GoogleSignInAccount
import com.google.android.gms.auth.api.signin.GoogleSignInClient
import com.google.android.gms.auth.api.signin.GoogleSignInOptions
import com.google.android.gms.common.api.ApiException
import okhttp3.*
import org.json.JSONObject
import java.io.IOException

class MainActivity : AppCompatActivity() {
    private lateinit var googleSignInClient: GoogleSignInClient
    private val RC_SIGN_IN = 1000

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        val gso = GoogleSignInOptions.Builder(GoogleSignInOptions.DEFAULT_SIGN_IN)
            .requestEmail()
            .requestIdToken("YOUR_GOOGLE_CLIENT_ID")
            .build()

        googleSignInClient = GoogleSignIn.getClient(this, gso)

        googleLoginButton.setOnClickListener {
            val signInIntent = googleSignInClient.signInIntent
            startActivityForResult(signInIntent, RC_SIGN_IN)
        }
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)

        if (requestCode == RC_SIGN_IN) {
            val task = GoogleSignIn.getSignedInAccountFromIntent(data)
            try {
                val account = task.getResult(ApiException::class.java)
                handleSignInResult(account)
            } catch (e: ApiException) {
                Log.e("GoogleLogin", "로그인 실패: ${e.statusCode}", e)
            }
        }
    }

    private fun handleSignInResult(account: GoogleSignInAccount?) {
        val accessToken = account?.idToken ?: return

        // 서버로 access_token 전송
        val url = "https://yourdomain.com/accounts/api/google/mobile/"
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
                Log.e("GoogleLogin", "서버 요청 실패", e)
            }

            override fun onResponse(call: Call, response: Response) {
                val responseBody = response.body?.string()
                val json = JSONObject(responseBody)

                if (json.getBoolean("success")) {
                    // 세션 쿠키 저장 (OkHttp가 자동으로 처리)
                    // 사용자 정보 저장
                    val user = json.getJSONObject("user")
                    val userId = user.getInt("id")
                    val email = user.getString("email")
                    val activityName = user.getString("activity_name")

                    // 실명 입력 필요 여부 확인
                    val requiresRealName = json.getBoolean("requires_real_name")
                    runOnUiThread {
                        if (requiresRealName) {
                            // 실명 입력 화면으로 이동
                            val intent = Intent(this@MainActivity, EnterRealNameActivity::class.java)
                            startActivity(intent)
                        } else {
                            // 메인 화면으로 이동
                            val intent = Intent(this@MainActivity, MainActivity::class.java)
                            startActivity(intent)
                        }
                    }
                } else {
                    val error = json.getString("error")
                    Log.e("GoogleLogin", "로그인 실패: $error")
                }
            }
        })
    }
}
```

### React Native

```javascript
import { GoogleSignin } from '@react-native-google-signin/google-signin';
import AsyncStorage from '@react-native-async-storage/async-storage';

GoogleSignin.configure({
  webClientId: 'YOUR_GOOGLE_CLIENT_ID',
});

const handleGoogleLogin = async () => {
  try {
    await GoogleSignin.hasPlayServices();
    const userInfo = await GoogleSignin.signIn();

    const tokens = await GoogleSignin.getTokens();
    const accessToken = tokens.idToken; // 서버 구현에 맞게 사용

    const response = await fetch('https://yourdomain.com/accounts/api/google/mobile/', {
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
      // 세션 쿠키는 자동으로 저장됨 (credentials: 'include')
      // 사용자 정보 저장
      await AsyncStorage.setItem('userId', data.user.id.toString());
      await AsyncStorage.setItem('userEmail', data.user.email);
      await AsyncStorage.setItem('activityName', data.user.activity_name);

      // 실명 입력 필요 여부 확인
      if (data.requires_real_name) {
        navigation.navigate('EnterRealName');
      } else {
        navigation.navigate('Home');
      }
    } else {
      console.error('로그인 실패:', data.error);
    }
  } catch (error) {
    console.error('구글 로그인 오류:', error);
  }
};
```

## 웹 기반 구글 로그인 (참고)

웹 브라우저에서는 기존 OAuth 2.0 방식의 엔드포인트를 사용합니다:

- **로그인 시작**: `GET /accounts/login/google/`
- **콜백 처리**: `GET /accounts/google/`

## 에러 처리

### 일반적인 에러 코드

- **400 Bad Request**: 요청 형식이 잘못되었거나 필수 파라미터가 누락됨
- **500 Internal Server Error**: 서버 내부 오류

### 에러 응답 예시

```json
{
  "success": false,
  "error": "구글 계정에서 이메일 정보를 제공하지 않았습니다."
}
```

## 보안 고려사항

1. **HTTPS 사용**: 프로덕션 환경에서는 반드시 HTTPS를 사용하세요.
2. **세션 관리**: 서버에서 세션 쿠키를 발급하므로, 이후 API 요청 시 쿠키를 포함해야 합니다.
3. **토큰 검증**: 서버는 구글 API를 통해 `access_token` 또는 `id_token`의 유효성을 검증합니다.
4. **클라이언트 ID/시크릿**: 클라이언트 시크릿은 서버에서만 사용하고, 앱에 포함하지 마세요.

## 추가 정보

- 구글 로그인 문서: https://developers.google.com/identity
- iOS 가이드: https://developers.google.com/identity/sign-in/ios
- Android 가이드: https://developers.google.com/identity/sign-in/android

