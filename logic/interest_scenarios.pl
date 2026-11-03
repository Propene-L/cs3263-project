% Phase 0.75 real-data visitor observations. These are test scenarios, not
% claims about real people. IDs point to imported ArtGraph records.

visitor_observation(obs_single_known_1, v_single, knows, ag_10472).
visitor_observation(obs_single_viewed_1, v_single, viewed, ag_10472).

visitor_observation(obs_multi_known_1, v_multi, knows, ag_10472).
visitor_observation(obs_multi_known_2, v_multi, knows, ag_37634).
visitor_observation(obs_multi_viewed_1, v_multi, viewed, ag_10472).
visitor_observation(obs_multi_viewed_2, v_multi, viewed, ag_37634).

visitor_observation(obs_positive_like_1, v_positive, likes, ag_10472).
visitor_observation(obs_positive_viewed_1, v_positive, viewed, ag_10472).

visitor_observation(obs_negative_like_1, v_negative, likes, ag_10472).
visitor_observation(obs_negative_dislike_1, v_negative, dislikes, ag_70351).
visitor_observation(obs_negative_viewed_1, v_negative, viewed, ag_10472).
visitor_observation(obs_negative_viewed_2, v_negative, viewed, ag_70351).

visitor_observation(obs_filtered_known_1, v_filtered, knows, ag_10472).
visitor_observation(obs_filtered_known_2, v_filtered, knows, ag_37634).
visitor_observation(obs_filtered_viewed_1, v_filtered, viewed, ag_10472).
visitor_observation(obs_filtered_viewed_2, v_filtered, viewed, ag_37634).
visitor_observation(obs_filtered_rejected_1, v_filtered, rejected, ag_70351).

